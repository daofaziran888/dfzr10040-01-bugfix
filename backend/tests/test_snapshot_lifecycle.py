"""快照生命周期与冷热分层测试。

验证分区快照的创建、版本标记、依赖追踪，以及冷热分层策略的管理。
"""
from __future__ import annotations

import pytest

from app.fusion_engine import FusionEngine
from app.recovery import CheckpointManager, ReplayQueue


@pytest.fixture
def engine() -> FusionEngine:
    return FusionEngine()


class TestSnapshotLifecycle:
    """分区快照生命周期测试。"""

    def test_create_snapshot(self, engine: FusionEngine) -> None:
        """创建分区快照。"""
        snap = engine.create_snapshot(
            target_wide_table="WT_ORDER",
            partition_key_value="20261118",
            dependency_partitions=["20261117"],
            schema_digest="SHA256-abc123",
        )
        assert snap.partition_code.startswith("SNAP-")
        assert snap.target_wide_table == "WT_ORDER"
        assert snap.partition_key_value == "20261118"
        assert snap.status_mark == "创建中"
        assert snap.record_count == 0

    def test_snapshot_states(self, engine: FusionEngine) -> None:
        """快照状态流转。"""
        snap = engine.create_snapshot(
            target_wide_table="WT_STATE",
            partition_key_value="20261118",
        )
        assert snap.status_mark == "创建中"

        snap.status_mark = "可用"
        assert snap.status_mark == "可用"

        snap.status_mark = "标记中"
        assert snap.status_mark == "标记中"

        snap.status_mark = "已过期"
        assert snap.status_mark == "已过期"

    def test_snapshot_with_dependencies(self, engine: FusionEngine) -> None:
        """带依赖的分区快照。"""
        snap = engine.create_snapshot(
            target_wide_table="WT_DEPS",
            partition_key_value="20261118",
            dependency_partitions=["20261116", "20261117"],
        )
        assert len(snap.dependency_partitions) == 2
        assert "20261116" in snap.dependency_partitions
        assert "20261117" in snap.dependency_partitions

    def test_fusion_pipeline_creates_snapshot(self, engine: FusionEngine) -> None:
        """融合流水线自动创建快照。"""
        engine.register_source(
            source_code="SRC-FS", source_name="fs_source", source_type="MySQL",
            connection_string="conn://fs",
        )
        job = engine.create_fusion_job(
            target_wide_table="WT_FS",
            participant_sources=["SRC-FS"],
            join_key="id",
        )
        result = engine.execute_fusion_pipeline(job.job_id)
        assert "snapshot" in result
        assert result["snapshot"]["record_count"] == 3

    def test_snapshot_record_tracking(self, engine: FusionEngine) -> None:
        """快照记录行数跟踪。"""
        snap = engine.create_snapshot(
            target_wide_table="WT_REC",
            partition_key_value="20261118",
        )
        assert snap.record_count == 0

        snap.record_count = 15000
        assert snap.record_count == 15000

        snap.record_count += 5000
        assert snap.record_count == 20000


class TestColdStoreStrategy:
    """冷热分层策略测试。"""

    def test_create_cold_store(self, engine: FusionEngine) -> None:
        """创建冷热分层策略。"""
        cs = engine.create_cold_store_strategy(
            target_wide_table="WT_ORDER",
            hot_data_days=7,
            cold_storage_type="orc",
            compression_method="snappy",
            migration_window="03:00-05:00",
        )
        assert cs.strategy_code.startswith("COLD-")
        assert cs.hot_data_days == 7
        assert cs.cold_storage_type == "orc"
        assert cs.compression_method == "snappy"

    def test_default_cold_store_values(self, engine: FusionEngine) -> None:
        """冷热分层默认值。"""
        cs = engine.create_cold_store_strategy(
            target_wide_table="WT_DEFAULT",
            hot_data_days=30,
        )
        assert cs.cold_storage_type == "parquet"
        assert cs.compression_method == "zstd"
        assert cs.migration_window == "02:00-06:00"

    def test_migration_with_partition_cutoff(self, engine: FusionEngine) -> None:
        """基于分区截止日期的迁移。"""
        cs = engine.create_cold_store_strategy(
            target_wide_table="WT_MIG", hot_data_days=3,
        )
        # 创建 5 个分区快照：20261101 到 20261105
        for i in range(1, 6):
            snap = engine.create_snapshot(
                target_wide_table="WT_MIG",
                partition_key_value=f"2026110{i}",
            )
            snap.record_count = 1000

        # 截止到 20261103：1和2被迁移，3-5保留
        result = engine.migrate_to_cold_store(
            cs.strategy_id, hot_partition_cutoff="20261103",
        )
        assert result["ok"] is True
        assert result["migrated_partitions"] == 2
        assert result["migrated_rows"] == 2000

    def test_multiple_cold_store_strategies(self, engine: FusionEngine) -> None:
        """多个冷热分层策略对不同宽表。"""
        cs1 = engine.create_cold_store_strategy(
            target_wide_table="WT_A", hot_data_days=7,
        )
        cs2 = engine.create_cold_store_strategy(
            target_wide_table="WT_B", hot_data_days=14,
        )
        assert cs1.strategy_code != cs2.strategy_code
        assert cs1.target_wide_table != cs2.target_wide_table


class TestPartitionStrategyAndArchive:
    """分区策略与归档协调测试。"""

    def test_create_partition_rule(self, engine: FusionEngine) -> None:
        """创建分区策略。"""
        pr = engine.create_partition_rule(
            target_wide_table="WT_PART",
            partition_type="range",
            partition_field="dt",
            retention_days=90,
            archive_policy="move_to_cold",
        )
        assert pr.strategy_code.startswith("PART-")
        assert pr.partition_type == "range"
        assert pr.retention_days == 90

    def test_archive_with_mismatched_strategies(self, engine: FusionEngine) -> None:
        """归档：策略不匹配时拒绝。"""
        pr = engine.create_partition_rule(
            target_wide_table="WT_A", partition_type="range",
            partition_field="dt", retention_days=30,
        )
        cs = engine.create_cold_store_strategy(
            target_wide_table="WT_B", hot_data_days=7,
        )
        result = engine.reconcile_partition_archive(
            pr.rule_id, cs.strategy_id,
        )
        assert result["ok"] is True
        assert result["archived_partitions"] == 0  # 不同宽表，无匹配

    def test_full_archive_workflow(self, engine: FusionEngine) -> None:
        """完整归档工作流：冷迁移 -> 归档。"""
        pr = engine.create_partition_rule(
            target_wide_table="WT_FULL", partition_type="range",
            partition_field="dt", retention_days=30,
            archive_policy="move_to_cold",
        )
        cs = engine.create_cold_store_strategy(
            target_wide_table="WT_FULL", hot_data_days=7,
        )
        # 创建快照
        for i in range(1, 4):
            snap = engine.create_snapshot(
                target_wide_table="WT_FULL",
                partition_key_value=f"2026110{i}",
            )
            snap.record_count = 500

        # 第一步：冷迁移
        result1 = engine.migrate_to_cold_store(
            cs.strategy_id, hot_partition_cutoff="20261201",
        )
        assert result1["migrated_partitions"] == 3

        # 第二步：归档
        result2 = engine.reconcile_partition_archive(
            pr.rule_id, cs.strategy_id,
        )
        assert result2["ok"] is True
        assert result2["archived_partitions"] == 3
        assert result2["archived_rows"] == 1500


class TestSnapshotExport:
    """快照导出测试。"""

    def test_export_from_valid_snapshot(self, engine: FusionEngine) -> None:
        """从有效快照导出数据。"""
        engine.register_source(
            source_code="SRC_ES", source_name="es_source", source_type="MySQL",
            connection_string="conn://es",
        )
        job = engine.create_fusion_job(
            target_wide_table="WT_ES",
            participant_sources=["SRC_ES"],
            join_key="id",
        )
        engine.execute_fusion_pipeline(job.job_id)

        snap = engine.create_snapshot(
            target_wide_table="WT_ES", partition_key_value="20261118",
        )
        plan = engine.create_export_plan(
            target_wide_table="WT_ES", export_format="csv",
            field_filter=["id", "name"],
        )
        result = engine.execute_export_from_snapshot(plan.plan_id, snap.partition_id)
        assert result["ok"] is True
        assert result["format"] == "csv"
        assert result["exported_rows"] == 3

    def test_export_with_row_limit(self, engine: FusionEngine) -> None:
        """导出带行数限制。"""
        engine.register_source(
            source_code="SRC_RL", source_name="rl_source", source_type="MySQL",
            connection_string="conn://rl",
        )
        job = engine.create_fusion_job(
            target_wide_table="WT_RL",
            participant_sources=["SRC_RL"],
            join_key="id",
        )
        engine.execute_fusion_pipeline(job.job_id)

        snap = engine.create_snapshot(
            target_wide_table="WT_RL", partition_key_value="20261118",
        )
        plan = engine.create_export_plan(
            target_wide_table="WT_RL", export_format="parquet",
            row_limit=1,
        )
        result = engine.execute_export_from_snapshot(plan.plan_id, snap.partition_id)
        assert result["ok"] is True
        assert result["exported_rows"] <= 1

    def test_export_nonexistent_snapshot(self, engine: FusionEngine) -> None:
        """从不存在快照导出时返回失败。"""
        plan = engine.create_export_plan(
            target_wide_table="WT_NE", export_format="parquet",
        )
        result = engine.execute_export_from_snapshot(plan.plan_id, 99999)
        assert result["ok"] is False
        assert "不存在" in result["message"]


class TestRecoveryReplay:
    """恢复与重放测试。"""

    def test_checkpoint_save_and_load(self) -> None:
        """检查点保存和加载。"""
        cm = CheckpointManager()
        cm.save_checkpoint("BACK_TASK_01", "5000", {"source": "WT_ORDER"})
        cp = cm.load_checkpoint("BACK_TASK_01")
        assert cp is not None
        assert cp["position"] == "5000"
        assert cp["metadata"]["source"] == "WT_ORDER"

    def test_checkpoint_clear(self) -> None:
        """检查点清除。"""
        cm = CheckpointManager()
        cm.save_checkpoint("TASK_X", "100")
        assert cm.clear_checkpoint("TASK_X") is True
        assert cm.load_checkpoint("TASK_X") is None
        assert cm.clear_checkpoint("NONEXISTENT") is False

    def test_replay_entry_enqueue(self) -> None:
        """重放条目入队。"""
        rq = ReplayQueue()
        entry = rq.enqueue(
            fusion_job_code="FUSI-0001",
            failure_reason="网络超时",
            backoff_strategy="exponential",
            max_retries=3,
        )
        assert entry.queue_status == "待重放"
        assert entry.can_retry() is True
        assert entry.next_backoff_seconds() == 2  # 2^1

    def test_replay_retry_cycle(self) -> None:
        """重放重试周期。"""
        rq = ReplayQueue()
        entry = rq.enqueue("FUSI-TEST", "临时失败", max_retries=2)

        assert rq.mark_retrying(entry.entry_id) is not None
        assert entry.queue_status == "重放中"

        # 第一次失败
        rq.increment_retry(entry.entry_id, "仍然失败")
        assert entry.retry_count == 1
        assert entry.queue_status == "待重放"

        # 第二次失败
        rq.increment_retry(entry.entry_id, "再次失败")
        assert entry.retry_count == 2
        assert entry.can_retry() is False
        assert entry.queue_status == "永久跳过"

    def test_replay_mark_success(self) -> None:
        """重放成功标记。"""
        rq = ReplayQueue()
        entry = rq.enqueue("FUSI-SUCC", "初始失败")
        rq.mark_retrying(entry.entry_id)
        rq.mark_success(entry.entry_id)
        assert entry.queue_status == "已恢复"

    def test_replay_dequeue(self) -> None:
        """重放条目出队。"""
        rq = ReplayQueue()
        entry = rq.enqueue("FUSI-DEQ", "失败")
        removed = rq.dequeue(entry.entry_id)
        assert removed is not None
        assert rq.dequeue(entry.entry_id) is None

    def test_replay_backoff_exponential(self) -> None:
        """指数退避计算。"""
        rq = ReplayQueue()
        entry = rq.enqueue("FUSI-BO", "失败", backoff_strategy="exponential", max_retries=5)
        # retry_count=0: 2^1 = 2
        assert entry.next_backoff_seconds() == 2
        entry.retry_count = 1
        assert entry.next_backoff_seconds() == 4
        entry.retry_count = 2
        assert entry.next_backoff_seconds() == 8
        entry.retry_count = 10
        assert entry.next_backoff_seconds() == 300  # capped

    def test_replay_backoff_linear(self) -> None:
        """线性退避计算。"""
        rq = ReplayQueue()
        entry = rq.enqueue("FUSI-LN", "失败", backoff_strategy="linear", max_retries=5)
        # retry_count=0: (0+1)*10 = 10
        assert entry.next_backoff_seconds() == 10
        entry.retry_count = 1
        assert entry.next_backoff_seconds() == 20
        entry.retry_count = 30
        assert entry.next_backoff_seconds() == 300  # capped

    def test_replay_with_checkpoint_data(self) -> None:
        """带检查点数据的重放。"""
        rq = ReplayQueue()
        cp_data = {"last_processed_key": "order_500", "batch_index": 5}
        entry = rq.enqueue(
            "FUSI-CP", "批次失败",
            checkpoint_data=cp_data,
        )
        assert entry.checkpoint_data["last_processed_key"] == "order_500"
        assert entry.checkpoint_data["batch_index"] == 5

    def test_checkpoint_manager_replay(self) -> None:
        """从检查点重放的完整体流程。"""
        cm = CheckpointManager()

        call_log: list[list[int]] = []

        def mock_replay_fn(batch: list[int], _start: int) -> dict:
            call_log.append(batch)
            if len(call_log) >= 2:
                return {"ok": False, "message": "模拟中断"}
            return {"ok": True}

        result = cm.replay_from_checkpoint(
            task_code="TASK-REPLAY",
            replay_fn=mock_replay_fn,
            total_items=5,
            batch_size=2,
        )
        assert result["ok"] is False
        assert not result["complete"]
        assert len(call_log) >= 1

    def test_checkpoint_recovery_log(self) -> None:
        """恢复日志记录。"""
        cm = CheckpointManager()
        cm.record_recovery("TASK-LOG", "action_start")
        cm.record_recovery("TASK-LOG", "action_complete", {"rows": 1000})
        log = cm.get_log()
        assert len(log) == 2
        assert log[0]["action"] == "action_start"
        assert log[1]["result"] == {"rows": 1000}