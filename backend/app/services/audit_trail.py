"""__NAME__领域服务：字段、状态和动作来自业务配置，数据处理骨架由基类复用。"""
from __future__ import annotations

from app.services.base import BaseModuleService


class AuditTrailService(BaseModuleService):
    MODULE = "audit_trail"
    ENTITY = "审计记录"
    OPERATION_TERM = "校验"
    LIST_FIELDS = ["记录编号", "变更目标", "操作人", "变更类型", "变更前后对比", "变更原因", "审批状态", "变更时间"]
    REQUIRED_FIELDS = ["记录编号", "变更目标", "操作人"]
    STATUS_ORDER = ["已记录", "待审批", "已通过", "已驳回"]
    ACTION_RULES = {"提交审批": "待审批", "确认通过": "已通过", "驳回变更": "已驳回"}
    NEGATIVE_ACTIONS = ["驳回变更"]
