"""__NAME__领域服务：字段、状态和动作来自业务配置，数据处理骨架由基类复用。"""
from __future__ import annotations

from app.services.base import BaseModuleService


class ReplayQueueService(BaseModuleService):
    MODULE = "replay_queue"
    ENTITY = "重放记录"
    OPERATION_TERM = "校验"
    LIST_FIELDS = ["记录编号", "融合作业", "失败原因", "重试次数", "退避策略", "最大重试", "最后重试", "队列状态"]
    REQUIRED_FIELDS = ["记录编号", "融合作业", "失败原因"]
    STATUS_ORDER = ["待重放", "重放中", "已恢复", "永久跳过"]
    ACTION_RULES = {"加入队列": "重放中", "手动重放": "已恢复", "永久跳过": "永久跳过"}
    NEGATIVE_ACTIONS = []
