# -*- coding: utf-8 -*-
"""
path_service.py
学海智导 (Xuehai Zhidao) V2 推荐学习路径应用服务 (Path Service)

职责：
1. 检索离线静态推荐学习路径与阶段分解
2. 配合动态路径状态服务提供全链路学习引导
"""

from typing import Any, Dict, Optional

from app.infrastructure.persistence.profile_repository import ProfileRepository


class PathService:
    """推荐学习路径应用服务"""

    def __init__(self, profile_repo: Optional[ProfileRepository] = None):
        self.repo = profile_repo or ProfileRepository

    def get_student_learning_path(self, student_id: str) -> Optional[Dict[str, Any]]:
        """获取单个学生的推荐学习路径与分阶段考点时序"""
        return self.repo.get_student_learning_path(student_id)

    def get_all_learning_paths(self) -> Dict[str, Any]:
        """获取全部学生的学习路径数据字典"""
        return self.repo.get_learning_paths()


# 全局默认单例
path_service = PathService()

__all__ = [
    "PathService",
    "path_service",
]
