"""__NAME__领域服务：字段、状态和动作来自业务配置，数据处理骨架由基类复用。"""
from __future__ import annotations

from app.services.base import BaseModuleService


class DimTableService(BaseModuleService):
    MODULE = "dim_table"
    ENTITY = "维度定义"
    OPERATION_TERM = "关联"
    LIST_FIELDS = ["维度编号", "维度名称", "主键字段", "层级结构", "缓慢变化策略", "生效区间", "关联宽表数", "最后刷新"]
    REQUIRED_FIELDS = ["维度编号", "维度名称", "主键字段"]
    STATUS_ORDER = ["草稿", "生效中", "版本更迭", "已停用"]
    ACTION_RULES = {"启效维度": "生效中", "版本更迭": "版本更迭", "停用维度": "已停用"}
    NEGATIVE_ACTIONS = ["停用维度"]
