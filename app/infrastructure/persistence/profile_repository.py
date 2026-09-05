# -*- coding: utf-8 -*-
"""
profile_repository.py
学海智导 (Xuehai Zhidao) V2 学生档案、学习路径与综合报告仓储层 (Profile Repository)

负责读取并缓存离线学生画像、学习路径与分析报告数据。
支持优先读取 data/seeds/ 种子文件，并在必要时优雅降级读取 output/ 目录。
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from app.core.config import settings


def _read_json_file(primary_path: Path, fallback_path: Optional[Path] = None) -> Dict[str, Any]:
    """读取 JSON 数据，优先 primary_path，次选 fallback_path"""
    target = primary_path if primary_path.exists() else fallback_path
    if target and target.exists():
        try:
            content = target.read_text(encoding="utf-8").strip()
            if content:
                return json.loads(content)
        except Exception:
            return {}
    return {}


class ProfileRepository:
    """学生档案、推荐路径与学情报告仓储"""

    _profiles_cache: Optional[Dict[str, Any]] = None
    _paths_cache: Optional[Dict[str, Any]] = None
    _reports_cache: Optional[Dict[str, Any]] = None

    @classmethod
    def _get_profiles_file(cls) -> Path:
        return settings.STUDENT_PROFILES_FILE

    @classmethod
    def _get_paths_file(cls) -> Path:
        return settings.LEARNING_PATHS_FILE

    @classmethod
    def _get_reports_file(cls) -> Path:
        return settings.STUDENT_REPORTS_FILE

    @classmethod
    def reload(cls) -> None:
        """清空内存缓存强制重新加载"""
        cls._profiles_cache = None
        cls._paths_cache = None
        cls._reports_cache = None

    @classmethod
    def get_profiles(cls) -> Dict[str, Any]:
        """获取全部学生基础画像字典 {student_id: profile}"""
        if cls._profiles_cache is None:
            fallback = settings.LEGACY_OUTPUT_DIR / "student_profiles.json"
            cls._profiles_cache = _read_json_file(cls._get_profiles_file(), fallback)
        return cls._profiles_cache

    @classmethod
    def get_student_profile(cls, student_id: str) -> Optional[Dict[str, Any]]:
        """获取单个学生画像数据"""
        profiles = cls.get_profiles()
        return profiles.get(student_id)

    @classmethod
    def get_learning_paths(cls) -> Dict[str, Any]:
        """获取全部学生推荐学习路径字典 {student_id: path_info}"""
        if cls._paths_cache is None:
            fallback = settings.LEGACY_OUTPUT_DIR / "learning_paths.json"
            cls._paths_cache = _read_json_file(cls._get_paths_file(), fallback)
        return cls._paths_cache

    @classmethod
    def get_student_learning_path(cls, student_id: str) -> Optional[Dict[str, Any]]:
        """获取单个学生推荐学习路径数据"""
        paths = cls.get_learning_paths()
        return paths.get(student_id)

    @classmethod
    def get_student_reports(cls) -> Dict[str, Any]:
        """获取全部学生综合分析报告字典 {student_id: report}"""
        if cls._reports_cache is None:
            fallback = settings.LEGACY_OUTPUT_DIR / "student_reports.json"
            cls._reports_cache = _read_json_file(cls._get_reports_file(), fallback)
        return cls._reports_cache

    @classmethod
    def get_student_report(cls, student_id: str) -> Optional[Dict[str, Any]]:
        """获取单个学生综合分析报告数据"""
        reports = cls.get_student_reports()
        return reports.get(student_id)

    @classmethod
    def get_all_student_ids(cls) -> List[str]:
        """获取所有有效学生编号列表"""
        return list(cls.get_profiles().keys())


# 全局默认单例实例
profile_repository = ProfileRepository()

__all__ = [
    "ProfileRepository",
    "profile_repository",
]
