"""__NAME__领域服务：字段、状态和动作来自业务配置，数据处理骨架由基类复用。"""
from __future__ import annotations

from app.services.base import BaseModuleService


class SnapshotMgrService(BaseModuleService):
    MODULE = "snapshot_mgr"
    ENTITY = "快照分区"
    OPERATION_TERM = "校验"
    LIST_FIELDS = ["分区编号", "目标宽表", "分区键值", "记录行数", "Schema摘要", "状态标记", "依赖分区", "创建时间"]
    REQUIRED_FIELDS = ["分区编号", "目标宽表", "分区键值"]
    STATUS_ORDER = ["创建中", "可用", "标记中", "已过期"]
    ACTION_RULES = {"创建快照": "可用", "标记版本": "标记中", "清理过期": "已过期"}
    NEGATIVE_ACTIONS = []
