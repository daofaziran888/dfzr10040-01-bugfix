"""__NAME__领域服务：字段、状态和动作来自业务配置，数据处理骨架由基类复用。"""
from __future__ import annotations

from app.services.base import BaseModuleService


class SchemaMapService(BaseModuleService):
    MODULE = "schema_map"
    ENTITY = "映射方案"
    OPERATION_TERM = "转换"
    LIST_FIELDS = ["方案编号", "源表名称", "目标宽表", "字段映射JSON", "类型转换", "缺失策略", "映射顺序", "方案状态"]
    REQUIRED_FIELDS = ["方案编号", "源表名称", "目标宽表"]
    STATUS_ORDER = ["草稿", "已发布", "映射异常", "已归档"]
    ACTION_RULES = {"发布方案": "已发布", "标记异常": "映射异常", "归档方案": "已归档"}
    NEGATIVE_ACTIONS = []
