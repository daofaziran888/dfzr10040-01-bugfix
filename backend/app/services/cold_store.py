"""__NAME__领域服务：字段、状态和动作来自业务配置，数据处理骨架由基类复用。"""
from __future__ import annotations

from app.services.base import BaseModuleService


class ColdStoreService(BaseModuleService):
    MODULE = "cold_store"
    ENTITY = "分层策略"
    OPERATION_TERM = "存储"
    LIST_FIELDS = ["策略编号", "目标宽表", "热数据天数", "冷存储类型", "迁移时间窗", "压缩方式", "已迁移行数", "最后迁移"]
    REQUIRED_FIELDS = ["策略编号", "目标宽表", "热数据天数"]
    STATUS_ORDER = ["待生效", "分层中", "已完成", "迁移异常"]
    ACTION_RULES = {"启效策略": "分层中", "暂停迁移": "已完成", "标记异常": "迁移异常"}
    NEGATIVE_ACTIONS = []
