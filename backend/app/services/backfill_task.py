"""__NAME__领域服务：字段、状态和动作来自业务配置，数据处理骨架由基类复用。"""
from __future__ import annotations

from app.services.base import BaseModuleService


class BackfillTaskService(BaseModuleService):
    MODULE = "backfill_task"
    ENTITY = "回填任务"
    OPERATION_TERM = "回填"
    LIST_FIELDS = ["任务编号", "目标宽表", "回填区间", "并行分区", "依赖检查", "断点位置", "已处理行", "剩余行数"]
    REQUIRED_FIELDS = ["任务编号", "目标宽表", "回填区间"]
    STATUS_ORDER = ["待回填", "回填中", "已完成", "回填失败"]
    ACTION_RULES = {"启动回填": "回填中", "暂停回填": "已完成", "标记失败": "回填失败"}
    NEGATIVE_ACTIONS = []
