"""__NAME__领域服务：字段、状态和动作来自业务配置，数据处理骨架由基类复用。"""
from __future__ import annotations

from app.services.base import BaseModuleService


class LineageEdgeService(BaseModuleService):
    MODULE = "lineage_edge"
    ENTITY = "血缘边"
    OPERATION_TERM = "转换"
    LIST_FIELDS = ["边编号", "上游节点", "下游节点", "关联字段", "转换函数", "关联类型", "依赖层级", "最后追踪"]
    REQUIRED_FIELDS = ["边编号", "上游节点", "下游节点"]
    STATUS_ORDER = ["已追踪", "已确认", "疑似缺失", "已废弃"]
    ACTION_RULES = {"确认血缘": "已确认", "标记缺失": "疑似缺失", "废弃边": "已废弃"}
    NEGATIVE_ACTIONS = []
