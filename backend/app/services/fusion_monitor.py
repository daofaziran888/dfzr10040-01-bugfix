"""__NAME__领域服务：字段、状态和动作来自业务配置，数据处理骨架由基类复用。"""
from __future__ import annotations

from app.services.base import BaseModuleService


class FusionMonitorService(BaseModuleService):
    MODULE = "fusion_monitor"
    ENTITY = "监控指标"
    OPERATION_TERM = "采集"
    LIST_FIELDS = ["指标编号", "融合作业", "监控维度", "采集间隔", "告警阈值", "告警渠道", "静默时段", "最近采样"]
    REQUIRED_FIELDS = ["指标编号", "融合作业", "监控维度"]
    STATUS_ORDER = ["待启用", "监控中", "已告警", "已静默"]
    ACTION_RULES = {"启用监控": "监控中", "静默告警": "已告警", "废弃监控": "已静默"}
    NEGATIVE_ACTIONS = []
