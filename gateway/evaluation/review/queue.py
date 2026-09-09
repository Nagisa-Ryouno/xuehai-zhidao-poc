# -*- coding: utf-8 -*-
"""
gateway.evaluation.review.queue
学海智导 (Xuehai Zhidao) V2 - Phase 3 / Sprint 7-D
Stage G4: Human Review Queue (人工复核升级队列)

设计原则：
1. 观察者语义：队列纯内存只读，仅记录分歧与高风险工单，绝不触发任何生产决策修改
2. 零业务状态副作用：不与 BKT/PathState 等业务系统产生反向联动
"""

from typing import List, Optional
from gateway.evaluation.review.models import HumanReviewItem


class HumanReviewQueue:
    """
    内存中人工复核升级队列管理器
    """

    def __init__(self):
        self._items: List[HumanReviewItem] = []

    def enqueue(self, item: HumanReviewItem) -> None:
        """入队新的待复核工单"""
        self._items.append(item)

    def get_pending_items(self) -> List[HumanReviewItem]:
        """获取当前所有待复核工单副本"""
        return list(self._items)

    def count(self) -> int:
        """返回队列中工单数量"""
        return len(self._items)

    def clear(self) -> None:
        """清空复核队列"""
        self._items.clear()
