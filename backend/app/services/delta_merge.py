"""__NAME__领域服务：字段、状态和动作来自业务配置，数据处理骨架由基类复用。"""
from __future__ import annotations

from app.services.base import BaseModuleService


class DeltaMergeService(BaseModuleService):
    MODULE = "delta_merge"
    ENTITY = "增量批次"
    OPERATION_TERM = "归并"
    LIST_FIELDS = ["批次编号", "融合作业", "归并键", "新增行数", "更新行数", "删除行数", "归并基线", "归并时间"]
    REQUIRED_FIELDS = ["批次编号", "融合作业", "归并键"]
    STATUS_ORDER = ["待归并", "归并中", "已完成", "归并冲突"]
    ACTION_RULES = {"启动归并": "归并中", "解决冲突": "归并冲突", "标记完成": "已完成"}
    NEGATIVE_ACTIONS = []
