"""__NAME__领域服务：字段、状态和动作来自业务配置，数据处理骨架由基类复用。"""
from __future__ import annotations

from app.services.base import BaseModuleService


class ExportSnapshotService(BaseModuleService):
    MODULE = "export_snapshot"
    ENTITY = "导出计划"
    OPERATION_TERM = "转换"
    LIST_FIELDS = ["计划编号", "目标宽表", "导出格式", "分区筛选", "字段筛选", "导出路径", "行数限制", "导出状态"]
    REQUIRED_FIELDS = ["计划编号", "目标宽表", "导出格式"]
    STATUS_ORDER = ["待导出", "导出中", "已完成", "导出失败"]
    ACTION_RULES = {"启动导出": "导出中", "取消导出": "已完成", "重试导出": "导出失败"}
    NEGATIVE_ACTIONS = []
