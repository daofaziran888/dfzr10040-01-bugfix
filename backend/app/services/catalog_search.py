"""__NAME__领域服务：字段、状态和动作来自业务配置，数据处理骨架由基类复用。"""
from __future__ import annotations

from app.services.base import BaseModuleService


class CatalogSearchService(BaseModuleService):
    MODULE = "catalog_search"
    ENTITY = "数据目录"
    OPERATION_TERM = "校验"
    LIST_FIELDS = ["目录编号", "宽表名称", "标签列表", "业务域", "负责人", "数据等级", "更新频率", "搜索权重"]
    REQUIRED_FIELDS = ["目录编号", "宽表名称", "标签列表"]
    STATUS_ORDER = ["草稿", "已发布", "需更新", "已下架"]
    ACTION_RULES = {"发布目录": "已发布", "标记更新": "需更新", "下架目录": "已下架"}
    NEGATIVE_ACTIONS = []
