"""__NAME__领域服务：字段、状态和动作来自业务配置，数据处理骨架由基类复用。"""
from __future__ import annotations

from app.services.base import BaseModuleService


class CrossValidateService(BaseModuleService):
    MODULE = "cross_validate"
    ENTITY = "校验方案"
    OPERATION_TERM = "关联"
    LIST_FIELDS = ["方案编号", "主体宽表", "参照宽表", "关联键", "校验字段", "偏差阈值", "最近结果", "校验状态"]
    REQUIRED_FIELDS = ["方案编号", "主体宽表", "参照宽表"]
    STATUS_ORDER = ["待校验", "校验中", "一致", "偏差告警"]
    ACTION_RULES = {"启动校验": "校验中", "确认一致": "一致", "标记偏差": "偏差告警"}
    NEGATIVE_ACTIONS = []
