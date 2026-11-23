"""快照版本依据与分段导出端到端测试。

复现并锁定以下场景：
- P1 确认时可查每批源数据版本和字段映射，第一次取数成功；
- 增量归并把订单 2 的 20 改成 99 后生成 P2，旧快照 P1 仍冻结 20；
- P1 第二次取数时分区服务暂时无法交付行片段，立即续读报缺交付依据，
  已交付键与续读范围可核，与实时数据核对出冲突但不污染确认值；
- 恢复服务后续读成功，P1 返回 20，P2 单独导出返回 99；
- 字段筛选不能混入其他版本新增的列。
"""
from __future__ import annotations

import json

import pytest

from app.fusion_engine import FusionEngine


@pytest.fixture
def engine() -> FusionEngine:
    return FusionEngine()


def _build_order_snapshot(engine: FusionEngine) -> tuple:
    """构建订单 1（amount=10）、订单 2（amount=20）的融合结果。"""
    engine.register_source(
        source_code="SRC-ORD", source_name="ods_order",
        source_type="MySQL", connection_string="conn://ord",
    )
    engine.create_schema_mapping(
        source_table="SRC-ORD", target_wide_table="WT_ORDER",
        field_mapping_json=json.dumps({"value": "amount"}),
    )
    job = engine.create_fusion_job(
        target_wide_table="WT_ORDER",
        participant_sources=["SRC-ORD"],
        join_key="id",
    )
    engine.execute_fusion_pipeline(job.job_id)

    # 只保留订单 1、2，并固定金额 10 / 20
    job.merged_records = job.merged_records[:2]
    job.merged_records[0]["amount"] = 10
    job.merged_records[1]["amount"] = 20
    return job


class TestVersionedSnapshotExport:
    """凭同一次确认证据出数的完整场景。"""

    def test_full_p1_interrupt_resume_and_p2_scenario(self, engine: FusionEngine) -> None:
        job = _build_order_snapshot(engine)

        # ---- P1：确认快照，冻结当次提交的完整版本依据 ----
        p1 = engine.create_snapshot("WT_ORDER", partition_key_value="20261123")
        confirm1 = engine.confirm_snapshot(
            p1.partition_id,
            schema_version="order-schema-v1",
            transform_version="transform-v1",
        )
        assert confirm1["ok"] is True
        assert confirm1["record_count"] == 2
        assert "amount" in confirm1["frozen_columns"]

        # P1 确认时能查到每批的源数据版本和字段映射
        evidence1 = engine.get_snapshot_evidence(p1.partition_id)
        assert evidence1["ok"] is True
        batch = evidence1["batch_evidence"][0]
        assert batch["source_version"]
        assert batch["field_mapping"] == {"value": "amount"}
        assert batch["raw_input_rows"] == 2
        order1_key, order2_key = evidence1["record_keys"]

        # ---- 选 amount 列分段下载，首批取数成功（订单 1）----
        plan = engine.create_export_plan(
            target_wide_table="WT_ORDER", export_format="csv",
            field_filter=["amount"],
        )
        seg1 = engine.start_segmented_export(
            plan.plan_id, p1.partition_id, batch_size=1,
        )
        assert seg1["ok"] is True
        assert seg1["schema_version"] == "order-schema-v1"
        assert seg1["rows"] == [{"amount": 10}]
        assert seg1["projection"] == ["amount"]
        assert seg1["batch_keys"] == [order1_key]
        assert seg1["cursor"] == 1
        assert seg1["finished"] is False
        session_id = seg1["session_id"]

        # ---- 增量归并更正第二批的一条记录：订单 2 的 20 -> 99 ----
        order2_id = job.merged_records[1]["id"]
        merge_result = engine.execute_delta_merge(job.job_id, [{
            "_source": "SRC-ORD", "id": order2_id,
            "amount": 99, "_op": "upsert",
        }])
        assert merge_result["ok"] is True
        assert merge_result["updated"] == 1
        live_order2 = next(r for r in job.merged_records if r["id"] == order2_id)
        assert live_order2["amount"] == 99

        # ---- 生成 P2（确认归并后的新版本）----
        p2 = engine.create_snapshot("WT_ORDER", partition_key_value="20261124")
        confirm2 = engine.confirm_snapshot(
            p2.partition_id,
            schema_version="order-schema-v2",
            transform_version="transform-v2",
        )
        assert confirm2["ok"] is True
        assert confirm2["evidence_id"] != confirm1["evidence_id"]

        # ---- P1 第二次取数：分区服务暂时无法交付行片段 ----
        offline = engine.set_partition_delivery_unavailable(
            p1.partition_id, reason="P1 第二次取数行片段交付中断",
        )
        assert offline["ok"] is True
        # 原始输入及转换版本仍然保留可核
        assert offline["retained_evidence"]["raw_inputs_verifiable"] is True
        assert offline["retained_evidence"]["transform_version"] == "transform-v1"

        # 立即续读：此时不能交付 P1 明细，并明确还缺哪项依据
        resume_fail = engine.resume_segmented_export(plan.plan_id, session_id)
        assert resume_fail["ok"] is False
        assert resume_fail["can_deliver"] is False
        assert resume_fail["code"] == "DELIVERY_UNAVAILABLE"
        assert any("delivery gate" in item for item in resume_fail["missing_evidence"])
        # 中断不推进游标，已交付的键和续读范围能核对
        assert resume_fail["cursor"] == 1
        assert resume_fail["delivered_keys"] == [order1_key]
        assert resume_fail["resume_range"] == [1, 2]
        retained = resume_fail["retained_evidence"]
        assert retained["raw_inputs_verifiable"] is True
        assert retained["schema_version"] == "order-schema-v1"

        # 与分区服务核对已确认片段：实时值 99 与确认值 20 冲突，仅报告不覆盖
        reconciliation = resume_fail["reconciliation"]
        assert reconciliation["consistent"] is False
        amount_conflict = next(
            c for c in reconciliation["conflicts"]
            if "amount" in c.get("fields", {})
        )
        assert amount_conflict["fields"]["amount"] == {"confirmed": 20, "current": 99}

        # ---- 恢复服务后续读：P1 仍返回确认时的 20 ----
        restored = engine.restore_partition_delivery(p1.partition_id)
        assert restored["delivery_available"] is True
        seg2 = engine.resume_segmented_export(plan.plan_id, session_id)
        assert seg2["ok"] is True
        assert seg2["rows"] == [{"amount": 20}]
        assert seg2["projection"] == ["amount"]  # 续读投影列不错位
        assert seg2["finished"] is True
        assert seg2["delivered_keys"] == [order1_key, order2_key]
        # 核对仍提示实时冲突，但出数严格取冻结证据
        assert seg2["reconciliation"]["consistent"] is False

        # ---- P1 整体导出仍是 10/20，P2 单独导出是 10/99 ----
        plan_p1 = engine.create_export_plan(
            target_wide_table="WT_ORDER", field_filter=["amount"],
        )
        export_p1 = engine.execute_export_from_snapshot(plan_p1.plan_id, p1.partition_id)
        assert export_p1["ok"] is True
        assert sorted(r["amount"] for r in export_p1["records"]) == [10, 20]
        assert export_p1["schema_version"] == "order-schema-v1"

        plan_p2 = engine.create_export_plan(
            target_wide_table="WT_ORDER", field_filter=["amount"],
        )
        export_p2 = engine.execute_export_from_snapshot(plan_p2.plan_id, p2.partition_id)
        assert export_p2["ok"] is True
        assert sorted(r["amount"] for r in export_p2["records"]) == [10, 99]
        assert export_p2["schema_version"] == "order-schema-v2"

    def test_field_filter_rejects_columns_from_other_versions(
        self, engine: FusionEngine
    ) -> None:
        _build_order_snapshot(engine)
        p1 = engine.create_snapshot("WT_ORDER", partition_key_value="20261123")
        engine.confirm_snapshot(p1.partition_id, schema_version="order-schema-v1")

        plan = engine.create_export_plan(
            target_wide_table="WT_ORDER",
            field_filter=["amount", "future_column"],
        )
        result = engine.start_segmented_export(
            plan.plan_id, p1.partition_id, batch_size=1,
        )
        assert result["ok"] is False
        assert result["code"] == "FIELD_NOT_IN_SNAPSHOT"
        assert "future_column" in result["message"]
        assert "amount" in result["frozen_columns"]

        full = engine.execute_export_from_snapshot(plan.plan_id, p1.partition_id)
        assert full["ok"] is False
        assert full["code"] == "FIELD_NOT_IN_SNAPSHOT"

    def test_row_limit_binds_to_frozen_snapshot_rows(self, engine: FusionEngine) -> None:
        _build_order_snapshot(engine)
        p1 = engine.create_snapshot("WT_ORDER", partition_key_value="20261123")
        engine.confirm_snapshot(p1.partition_id)

        plan = engine.create_export_plan(
            target_wide_table="WT_ORDER", field_filter=["amount"], row_limit=1,
        )
        seg = engine.start_segmented_export(
            plan.plan_id, p1.partition_id, batch_size=1,
        )
        # 条数上限对应选定快照：首批即最后一批，总计 1 条
        assert seg["total"] == 1
        assert seg["rows"] == [{"amount": 10}]
        assert seg["finished"] is True

    def test_unconfirmed_old_partition_reports_missing_evidence(
        self, engine: FusionEngine
    ) -> None:
        _build_order_snapshot(engine)
        old = engine.create_snapshot("WT_ORDER", partition_key_value="20261101")
        old.record_count = 2  # 只有编号和计数，未确认

        plan = engine.create_export_plan(target_wide_table="WT_ORDER")
        result = engine.start_segmented_export(
            plan.plan_id, old.partition_id, batch_size=1,
        )
        assert result["ok"] is False
        assert result["code"] == "EVIDENCE_MISSING"
        assert result["missing_evidence"]

        evidence = engine.get_snapshot_evidence(old.partition_id)
        assert evidence["ok"] is False
        assert evidence["code"] == "EVIDENCE_MISSING"
