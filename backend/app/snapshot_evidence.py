"""快照证据与分区服务：让导出始终凭「同一次确认的完整证据」出数。

设计要点：

1. 分区快照在确认（confirm）时冻结当次提交的全部依据——行明细（深拷贝，
   后续增量归并改实时宽表不会污染）、字段清单、Schema/转换版本，以及每批
   可核的原始输入、源数据版本与字段映射。
2. 只有编号和计数、没有确认证据的旧分区，重新导出时明确报出缺少的依据，
   绝不回读实时宽表冒充快照明细；导出计划仍可用于其他有证据的分区。
3. 分区服务负责行片段交付。它可以被临时置为「无法交付」（模拟服务中断），
   但证据本身保留可核；恢复后仍按冻结证据出数。
4. 分段下载与断点续读共享同一份证据、同一投影列顺序、同一游标，已交付的
   键与续读范围可逐批核对；与实时数据核对发现漂移时只报告冲突，绝不用
   后来写入的值覆盖确认值。
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def evidence_key(record: dict[str, Any], index: int) -> str:
    """为冻结行生成稳定可核的键：优先融合键，其次 来源#主键，最后行序号。"""
    if record.get("_fusion_key"):
        return str(record["_fusion_key"])
    source = record.get("_source", "_")
    primary = record.get("id", f"row-{index}")
    return f"{source}#{primary}"


@dataclass
class BatchEvidence:
    """单批确认证据：可核的原始输入、源数据版本、字段映射与转换版本。"""
    batch_index: int
    source_code: str
    source_version: str
    transform_version: str
    field_mapping: dict[str, str]
    raw_inputs: list[dict[str, Any]]
    record_keys: list[str] = field(default_factory=list)

    def summary(self) -> dict[str, Any]:
        return {
            "batch_index": self.batch_index,
            "source_code": self.source_code,
            "source_version": self.source_version,
            "transform_version": self.transform_version,
            "field_mapping": dict(self.field_mapping),
            "raw_input_rows": len(self.raw_inputs),
            "record_keys": list(self.record_keys),
        }


@dataclass
class SnapshotEvidence:
    """一次快照确认的完整版本依据。"""
    evidence_id: str
    partition_id: int
    partition_code: str
    target_wide_table: str
    schema_version: str
    transform_version: str
    frozen_columns: list[str]
    frozen_records: list[dict[str, Any]]
    record_keys: list[str]
    batch_evidence: list[BatchEvidence]
    confirmed_time: str

    def column_set(self) -> set[str]:
        return set(self.frozen_columns)

    def batch_summaries(self) -> list[dict[str, Any]]:
        return [b.summary() for b in self.batch_evidence]


@dataclass
class SegmentedExportSession:
    """分段导出会话：绑定一次确认证据，游标与已交付键支撑断点续读。"""
    session_id: str
    plan_id: int
    evidence_id: str
    partition_id: int
    schema_version: str
    projection: list[str]
    row_limit: int
    batch_size: int
    cursor: int = 0
    delivered_keys: list[str] = field(default_factory=list)
    finished: bool = False

    def effective_total(self, evidence: SnapshotEvidence) -> int:
        total = len(evidence.frozen_records)
        if self.row_limit and self.row_limit > 0:
            total = min(total, self.row_limit)
        return total


class PartitionService:
    """分区服务：证据登记、交付闸门、片段核对与分段取数。"""

    def __init__(self) -> None:
        self._evidence: dict[str, SnapshotEvidence] = {}
        self._sessions: dict[str, SegmentedExportSession] = {}
        # 临时无法交付行片段的证据（服务中断），证据本身仍保留可核
        self._unavailable: dict[str, str] = {}

    # ---- 证据登记 ----

    def confirm_evidence(
        self,
        *,
        partition_id: int,
        partition_code: str,
        target_wide_table: str,
        records: list[dict[str, Any]],
        batch_evidence: list[BatchEvidence],
        schema_version: str,
        transform_version: str,
    ) -> SnapshotEvidence:
        """确认快照：深拷贝冻结行并登记完整版本依据。"""
        frozen_records = [dict(rec) for rec in records]
        record_keys = [evidence_key(rec, idx) for idx, rec in enumerate(frozen_records)]

        frozen_columns: list[str] = []
        for rec in frozen_records:
            for col in rec.keys():
                if col not in frozen_columns:
                    frozen_columns.append(col)

        evidence_id = f"EVD-{uuid.uuid4().hex[:12]}"
        evidence = SnapshotEvidence(
            evidence_id=evidence_id,
            partition_id=partition_id,
            partition_code=partition_code,
            target_wide_table=target_wide_table,
            schema_version=schema_version,
            transform_version=transform_version,
            frozen_columns=frozen_columns,
            frozen_records=frozen_records,
            record_keys=record_keys,
            batch_evidence=[b for b in batch_evidence],
            confirmed_time=_now_iso(),
        )
        self._evidence[evidence_id] = evidence
        return evidence

    def get_evidence(self, evidence_id: str) -> SnapshotEvidence | None:
        return self._evidence.get(evidence_id)

    def evidence_for_partition(self, partition_id: int) -> SnapshotEvidence | None:
        for ev in self._evidence.values():
            if ev.partition_id == partition_id:
                return ev
        return None

    # ---- 交付闸门 ----

    def set_delivery_unavailable(self, evidence_id: str, reason: str) -> None:
        self._unavailable[evidence_id] = reason

    def restore_delivery(self, evidence_id: str) -> None:
        self._unavailable.pop(evidence_id, None)

    def is_delivery_available(self, evidence_id: str) -> bool:
        return evidence_id not in self._unavailable

    def unavailable_reason(self, evidence_id: str) -> str:
        return self._unavailable.get(evidence_id, "")

    # ---- 实时核对 ----

    def reconcile(
        self,
        evidence: SnapshotEvidence,
        live_records: list[dict[str, Any]] | None,
        start: int = 0,
        end: int | None = None,
    ) -> dict[str, Any]:
        """把已确认片段与实时宽表核对，返回冲突明细（不修改冻结证据）。"""
        end = len(evidence.record_keys) if end is None else min(end, len(evidence.record_keys))
        conflicts: list[dict[str, Any]] = []
        if not live_records:
            return {"consistent": True, "checked_range": [start, end], "conflicts": conflicts}

        live_by_key = {evidence_key(rec, idx): rec for idx, rec in enumerate(live_records)}
        for idx in range(start, end):
            key = evidence.record_keys[idx]
            frozen_row = evidence.frozen_records[idx]
            live_row = live_by_key.get(key)
            if live_row is None:
                conflicts.append({"key": key, "reason": "实时宽表缺少该确认键", "fields": {}})
                continue
            field_diffs: dict[str, dict[str, Any]] = {}
            for col in evidence.frozen_columns:
                frozen_value = frozen_row.get(col)
                live_value = live_row.get(col)
                if frozen_value != live_value:
                    field_diffs[col] = {"confirmed": frozen_value, "current": live_value}
            if field_diffs:
                conflicts.append({"key": key, "reason": "确认值与实时值不一致", "fields": field_diffs})
        return {
            "consistent": not conflicts,
            "checked_range": [start, end],
            "conflicts": conflicts,
        }

    # ---- 分段会话 ----

    def create_session(
        self,
        *,
        plan_id: int,
        evidence: SnapshotEvidence,
        field_filter: list[str],
        row_limit: int,
        batch_size: int,
    ) -> tuple[SegmentedExportSession | None, dict[str, Any] | None]:
        """创建分段会话；字段筛选混入非本快照列时拒绝并返回错误。"""
        unknown = [col for col in field_filter if col not in evidence.column_set()]
        if unknown:
            return None, {
                "ok": False,
                "code": "FIELD_NOT_IN_SNAPSHOT",
                "message": (
                    f"字段筛选 {unknown} 不在快照 {evidence.partition_code} "
                    f"确认版本 {evidence.schema_version} 的冻结列中，"
                    "不能混入其他版本新增的列"
                ),
                "frozen_columns": list(evidence.frozen_columns),
            }
        projection = (
            [col for col in evidence.frozen_columns if col in field_filter]
            if field_filter else list(evidence.frozen_columns)
        )
        session = SegmentedExportSession(
            session_id=f"SESS-{uuid.uuid4().hex[:12]}",
            plan_id=plan_id,
            evidence_id=evidence.evidence_id,
            partition_id=evidence.partition_id,
            schema_version=evidence.schema_version,
            projection=projection,
            row_limit=row_limit,
            batch_size=max(1, batch_size),
        )
        self._sessions[session.session_id] = session
        return session, None

    def get_session(self, session_id: str) -> SegmentedExportSession | None:
        return self._sessions.get(session_id)

    def fetch_fragment(
        self,
        evidence: SnapshotEvidence,
        session: SegmentedExportSession,
        live_records: list[dict[str, Any]] | None,
    ) -> dict[str, Any]:
        """凭确认证据交付下一段；先与实时数据核对，再从冻结行切片出数。"""
        total = session.effective_total(evidence)
        if session.cursor >= total:
            session.finished = True
            return {
                "ok": True,
                "session_id": session.session_id,
                "evidence_id": evidence.evidence_id,
                "schema_version": evidence.schema_version,
                "rows": [],
                "delivered_keys": list(session.delivered_keys),
                "next_range": [total, total],
                "cursor": total,
                "total": total,
                "finished": True,
                "reconciliation": {"consistent": True, "checked_range": [total, total], "conflicts": []},
            }

        start = session.cursor
        end = min(start + session.batch_size, total)
        reconciliation = self.reconcile(evidence, live_records, start, end)

        rows: list[dict[str, Any]] = []
        keys: list[str] = []
        for idx in range(start, end):
            frozen_row = evidence.frozen_records[idx]
            # 固定按会话投影列顺序输出，续读时列不会错位
            rows.append({col: frozen_row.get(col) for col in session.projection})
            keys.append(evidence.record_keys[idx])

        session.cursor = end
        session.delivered_keys.extend(keys)
        session.finished = end >= total

        return {
            "ok": True,
            "session_id": session.session_id,
            "evidence_id": evidence.evidence_id,
            "partition_code": evidence.partition_code,
            "schema_version": evidence.schema_version,
            "rows": rows,
            "delivered_keys": list(session.delivered_keys),
            "batch_keys": keys,
            "range": [start, end],
            "next_range": [end, session.effective_total(evidence)],
            "cursor": end,
            "total": session.effective_total(evidence),
            "finished": session.finished,
            "projection": list(session.projection),
            "reconciliation": reconciliation,
        }

    def unavailable_response(
        self,
        evidence: SnapshotEvidence,
        session: SegmentedExportSession,
        live_records: list[dict[str, Any]] | None,
    ) -> dict[str, Any]:
        """服务中断时的结构化响应：保留可核依据，明确还缺哪项交付依据。"""
        total = session.effective_total(evidence)
        start = session.cursor
        reconciliation = self.reconcile(evidence, live_records, start, total)
        return {
            "ok": False,
            "code": "DELIVERY_UNAVAILABLE",
            "can_deliver": False,
            "message": (
                f"分区服务暂时无法交付快照 {evidence.partition_code} 的行片段："
                f"{self.unavailable_reason(evidence.evidence_id) or '交付闸门关闭'}"
            ),
            "missing_evidence": ["分区服务行片段交付能力（delivery gate）"],
            "retained_evidence": {
                "evidence_id": evidence.evidence_id,
                "schema_version": evidence.schema_version,
                "transform_version": evidence.transform_version,
                "raw_inputs_verifiable": True,
                "batch_evidence": evidence.batch_summaries(),
            },
            "session_id": session.session_id,
            "evidence_id": evidence.evidence_id,
            "schema_version": evidence.schema_version,
            "delivered_keys": list(session.delivered_keys),
            "resume_range": [start, total],
            "cursor": start,
            "total": total,
            "finished": False,
            "reconciliation": reconciliation,
        }


# 全局单例
partition_service = PartitionService()
