"""__NAME__领域服务：字段、状态和动作来自业务配置，数据处理骨架由基类复用。"""
from __future__ import annotations

from app.services.base import BaseModuleService


class DataDriftService(BaseModuleService):
    MODULE = "data_drift"
    ENTITY = "漂移记录"
    OPERATION_TERM = "校验"
    LIST_FIELDS = ["记录编号", "宽表名称", "漂移类型", "历史基线", "当前分布", "KL散度", "漂移方向", "检测时间"]
    REQUIRED_FIELDS = ["记录编号", "宽表名称", "漂移类型"]
    STATUS_ORDER = ["已检测", "评估中", "已确认", "可忽略"]
    ACTION_RULES = {"发起评估": "评估中", "确认漂移": "已确认", "忽略变化": "可忽略"}
    NEGATIVE_ACTIONS = ["忽略变化"]
