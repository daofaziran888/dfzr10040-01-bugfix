"""__NAME__领域服务：字段、状态和动作来自业务配置，数据处理骨架由基类复用。"""
from __future__ import annotations

from app.services.base import BaseModuleService


class MetricAggrService(BaseModuleService):
    MODULE = "metric_aggr"
    ENTITY = "聚合规则"
    OPERATION_TERM = "聚合"
    LIST_FIELDS = ["规则编号", "目标宽表", "聚合函数", "分组维度", "时间粒度", "预计算窗口", "存储表名", "最近计算"]
    REQUIRED_FIELDS = ["规则编号", "目标宽表", "聚合函数"]
    STATUS_ORDER = ["待计算", "计算中", "已物化", "需重建"]
    ACTION_RULES = {"触发计算": "计算中", "重建物化": "已物化", "标记失效": "需重建"}
    NEGATIVE_ACTIONS = []
