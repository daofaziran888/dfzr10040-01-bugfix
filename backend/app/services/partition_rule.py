"""__NAME__领域服务：字段、状态和动作来自业务配置，数据处理骨架由基类复用。"""
from __future__ import annotations

from app.services.base import BaseModuleService


class PartitionRuleService(BaseModuleService):
    MODULE = "partition_rule"
    ENTITY = "分区定义"
    OPERATION_TERM = "归档"
    LIST_FIELDS = ["策略编号", "目标宽表", "分区类型", "分区字段", "保留天数", "归档策略", "分区数量", "最后调整"]
    REQUIRED_FIELDS = ["策略编号", "目标宽表", "分区类型"]
    STATUS_ORDER = ["草稿", "生效中", "需调整", "已废弃"]
    ACTION_RULES = {"启效策略": "生效中", "调整策略": "需调整", "废弃策略": "已废弃"}
    NEGATIVE_ACTIONS = []
