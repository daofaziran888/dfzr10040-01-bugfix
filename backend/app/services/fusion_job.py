"""__NAME__领域服务：字段、状态和动作来自业务配置，数据处理骨架由基类复用。"""
from __future__ import annotations

from app.services.base import BaseModuleService


class FusionJobService(BaseModuleService):
    MODULE = "fusion_job"
    ENTITY = "融合任务"
    OPERATION_TERM = "关联"
    LIST_FIELDS = ["作业编号", "目标宽表", "参与数据源", "关联键", "融合窗口", "水位线字段", "输出行数", "跳过行数"]
    REQUIRED_FIELDS = ["作业编号", "目标宽表", "参与数据源"]
    STATUS_ORDER = ["待执行", "融合中", "已完成", "部分失败"]
    ACTION_RULES = {"启动融合": "融合中", "暂停作业": "已完成", "标记完成": "部分失败"}
    NEGATIVE_ACTIONS = []
