"""__NAME__领域服务：字段、状态和动作来自业务配置，数据处理骨架由基类复用。"""
from __future__ import annotations

from app.services.base import BaseModuleService


class SourceDefService(BaseModuleService):
    MODULE = "source_def"
    ENTITY = "数据源"
    OPERATION_TERM = "接入"
    LIST_FIELDS = ["源编号", "源名称", "源类型", "连接串", "认证方式", "字符编码", "时区设置", "接入状态"]
    REQUIRED_FIELDS = ["源编号", "源名称", "源类型"]
    STATUS_ORDER = ["待验证", "已接入", "连接异常", "已停用"]
    ACTION_RULES = {"验证连接": "已接入", "标记异常": "连接异常", "停用数据源": "已停用"}
    NEGATIVE_ACTIONS = ["停用数据源"]
