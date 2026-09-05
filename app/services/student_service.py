# -*- coding: utf-8 -*-
"""
student_service.py
学海智导 (Xuehai Zhidao) V2 学生应用服务与全景档案聚合层 (Student Service)

职责：
1. 聚合查询学生画像、推荐路径与综合报告 (Dashboard Aggregation)
2. 提供系统宏观概况数据 (System Overview)
3. 提供学生花名册与学情列表查询
"""

from typing import Any, Dict, List, Optional

from app.infrastructure.persistence.profile_repository import ProfileRepository


class StudentService:
    """学生学情、档案与全景看板聚合应用服务"""

    def __init__(self, profile_repo: Optional[ProfileRepository] = None):
        self.repo = profile_repo or ProfileRepository

    def get_system_overview(self) -> Dict[str, Any]:
        """获取系统宏观概况数据"""
        profiles = self.repo.get_profiles()
        paths = self.repo.get_learning_paths()
        reports = self.repo.get_student_reports()

        students_summary = []
        for sid, p in profiles.items():
            name = p.get("student", {}).get("student_name", "")
            students_summary.append({"student_id": sid, "student_name": name})

        return {
            "student_count": len(profiles),
            "profile_count": len(profiles),
            "learning_path_count": len(paths),
            "report_count": len(reports),
            "students": students_summary,
        }

    def get_all_students(self) -> List[Dict[str, Any]]:
        """获取全部学生学情卡片列表"""
        profiles = self.repo.get_profiles()
        students: List[Dict[str, Any]] = []

        for sid, profile in profiles.items():
            st = profile.get("student", {})
            overall = profile.get("overall_profile", {})
            students.append({
                "student_id": sid,
                "student_name": st.get("student_name", ""),
                "major": st.get("major", ""),
                "grade": st.get("grade", ""),
                "learning_goal": st.get("learning_goal", ""),
                "class_name": st.get("class_name", ""),
                "average_accuracy": overall.get("average_accuracy", 0.0),
                "answer_time_seconds": overall.get("answer_time_seconds", 0.0),
                "practice_count": overall.get("practice_count", 0),
                "mastery_level": overall.get("mastery_level", ""),
                "activity_level": overall.get("activity_level", ""),
                "completion_level": overall.get("completion_level", ""),
                "weak_knowledge_count": len(profile.get("weak_knowledge_points", [])),
                "prerequisite_knowledge_count": len(profile.get("prerequisite_knowledge_points", [])),
            })
        return students

    def get_student_profile(self, student_id: str) -> Optional[Dict[str, Any]]:
        """获取单个学生画像"""
        return self.repo.get_student_profile(student_id)

    def get_student_report(self, student_id: str) -> Optional[Dict[str, Any]]:
        """获取单个学生综合报告"""
        return self.repo.get_student_report(student_id)

    def get_all_reports(self) -> Dict[str, Any]:
        """获取全部学生报告"""
        return self.repo.get_student_reports()

    def get_student_dashboard(self, student_id: str) -> Optional[Dict[str, Any]]:
        """聚合获取学生完整仪表盘数据（画像 + 推荐路径 + 报告）"""
        profiles = self.repo.get_profiles()
        if student_id not in profiles:
            return None

        paths = self.repo.get_learning_paths()
        reports = self.repo.get_student_reports()

        return {
            "student_id": student_id,
            "profile": profiles.get(student_id),
            "learning_path": paths.get(student_id),
            "report": reports.get(student_id),
        }


# 全局默认单例
student_service = StudentService()

__all__ = [
    "StudentService",
    "student_service",
]
