"""__NAME__领域服务：字段、状态和动作来自业务配置，数据处理骨架由基类复用。"""
from __future__ import annotations

from app.services.base import BaseModuleService


class MergeConflictService(BaseModuleService):
    MODULE = "merge_conflict"
    ENTITY = "冲突规则"
    OPERATION_TERM = "校验"
    LIST_FIELDS = ["规则编号", "目标宽表", "冲突字段", "仲裁策略", "优先级来源", "时间基准", "冲突记录数", "规则状态"]
    REQUIRED_FIELDS = ["规则编号", "目标宽表", "冲突字段"]
    STATUS_ORDER = ["草稿", "生效中", "仲裁异常", "已停用"]
    ACTION_RULES = {"启效规则": "生效中", "标记异常": "仲裁异常", "停用规则": "已停用"}
    NEGATIVE_ACTIONS = ["停用规则"]
