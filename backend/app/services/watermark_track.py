"""__NAME__领域服务：字段、状态和动作来自业务配置，数据处理骨架由基类复用。"""
from __future__ import annotations

from app.services.base import BaseModuleService


class WatermarkTrackService(BaseModuleService):
    MODULE = "watermark_track"
    ENTITY = "水位记录"
    OPERATION_TERM = "水位"
    LIST_FIELDS = ["记录编号", "数据源", "当前水位", "上次水位", "推进间隔", "延迟分钟", "数据来源", "最后推进"]
    REQUIRED_FIELDS = ["记录编号", "数据源", "当前水位"]
    STATUS_ORDER = ["待初始化", "正常推进", "延迟告警", "停滞"]
    ACTION_RULES = {"初始化水位": "正常推进", "确认告警": "延迟告警", "手动推进": "停滞"}
    NEGATIVE_ACTIONS = []
