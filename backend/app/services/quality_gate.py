"""__NAME__领域服务：字段、状态和动作来自业务配置，数据处理骨架由基类复用。"""
from __future__ import annotations

from app.services.base import BaseModuleService


class QualityGateService(BaseModuleService):
    MODULE = "quality_gate"
    ENTITY = "门禁规则"
    OPERATION_TERM = "校验"
    LIST_FIELDS = ["规则编号", "目标宽表", "检查类型", "阈值条件", "触发动作", "阻断级别", "检查行数", "最近触发"]
    REQUIRED_FIELDS = ["规则编号", "目标宽表", "检查类型"]
    STATUS_ORDER = ["待启用", "生效中", "已触发", "已关闭"]
    ACTION_RULES = {"启用门禁": "生效中", "临时关闭": "已触发", "恢复门禁": "已关闭"}
    NEGATIVE_ACTIONS = []
