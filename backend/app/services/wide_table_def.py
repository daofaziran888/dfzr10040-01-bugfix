"""__NAME__领域服务：字段、状态和动作来自业务配置，数据处理骨架由基类复用。"""
from __future__ import annotations

from app.services.base import BaseModuleService


class WideTableDefService(BaseModuleService):
    MODULE = "wide_table_def"
    ENTITY = "宽表元数据"
    OPERATION_TERM = "校验"
    LIST_FIELDS = ["表编号", "宽表名称", "字段列表", "主键定义", "分区键", "TTL天数", "数据来源数", "最近更新"]
    REQUIRED_FIELDS = ["表编号", "宽表名称", "字段列表"]
    STATUS_ORDER = ["设计期", "生效中", "Schema变更", "已下架"]
    ACTION_RULES = {"发布宽表": "生效中", "标记变更": "Schema变更", "下架宽表": "已下架"}
    NEGATIVE_ACTIONS = []
