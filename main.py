# -*- coding: utf-8 -*-

"""
学海智导 POC
FastAPI 后端

第四阶段：
将前面三个阶段生成的 JSON 数据
通过 REST API 提供给前端。

数据来源：

student_profiles.json
learning_paths.json
student_reports.json
"""

import json
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware


# ============================================================
# 基础配置
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

OUTPUT_DIR = BASE_DIR / "output"

PROFILE_FILE = OUTPUT_DIR / "student_profiles.json"
PATH_FILE = OUTPUT_DIR / "learning_paths.json"
REPORT_FILE = OUTPUT_DIR / "student_reports.json"


# ============================================================
# 创建 FastAPI 应用
# ============================================================

app = FastAPI(
    title="学海智导 API",
    description="AI驱动的个性化学习与学情分析平台 POC",
    version="0.1.0"
)


# ============================================================
# CORS
# ============================================================

app.add_middleware(
    CORSMiddleware,

    allow_origins=["*"],

    allow_credentials=True,

    allow_methods=["*"],

    allow_headers=["*"],
)


# ============================================================
# 工具函数
# ============================================================

def load_json(file_path: Path):
    """
    读取 JSON 文件
    """

    if not file_path.exists():

        raise HTTPException(
            status_code=500,
            detail=f"数据文件不存在：{file_path}"
        )

    try:

        with open(
            file_path,
            "r",
            encoding="utf-8"
        ) as f:

            return json.load(f)

    except json.JSONDecodeError:

        raise HTTPException(
            status_code=500,
            detail=f"JSON 文件格式错误：{file_path}"
        )


# ============================================================
# 首页
# ============================================================

@app.get("/")
def root():

    return {
        "message": "学海智导 API 正常运行",
        "version": "0.1.0",
        "status": "running"
    }


# ============================================================
# 系统健康检查
# ============================================================

@app.get("/api/health")
def health_check():

    return {
        "status": "ok",

        "files": {
            "student_profiles": PROFILE_FILE.exists(),
            "learning_paths": PATH_FILE.exists(),
            "student_reports": REPORT_FILE.exists()
        }
    }


# ============================================================
# 获取所有学生
# ============================================================

@app.get("/api/students")
def get_students():

    profiles = load_json(
        PROFILE_FILE
    )

    students = []

    for student_id, profile in profiles.items():

        student = profile.get(
            "student",
            {}
        )

        overall = profile.get(
            "overall_profile",
            {}
        )

        students.append({

            "student_id":
                student_id,

            "student_name":
                student.get(
                    "student_name"
                ),

            "major":
                student.get(
                    "major"
                ),

            "grade":
                student.get(
                    "grade"
                ),

            "learning_goal":
                student.get(
                    "learning_goal"
                ),

            "average_accuracy":
                overall.get(
                    "average_accuracy"
                ),

            "mastery_level":
                overall.get(
                    "mastery_level"
                ),

            "activity_level":
                overall.get(
                    "activity_level"
                ),

            "completion_level":
                overall.get(
                    "completion_level"
                )
        })

    return {
        "count": len(students),
        "students": students
    }


# ============================================================
# 获取单个学生画像
# ============================================================

@app.get("/api/students/{student_id}/profile")
def get_student_profile(
    student_id: str
):

    profiles = load_json(
        PROFILE_FILE
    )

    if student_id not in profiles:

        raise HTTPException(
            status_code=404,
            detail=f"学生不存在：{student_id}"
        )

    return profiles[
        student_id
    ]


# ============================================================
# 获取单个学生学习路径
# ============================================================

@app.get("/api/students/{student_id}/learning-path")
def get_learning_path(
    student_id: str
):

    paths = load_json(
        PATH_FILE
    )

    if student_id not in paths:

        raise HTTPException(
            status_code=404,
            detail=f"学生不存在：{student_id}"
        )

    return paths[
        student_id
    ]


# ============================================================
# 获取单个学生综合报告
# ============================================================

@app.get("/api/students/{student_id}/report")
def get_student_report(
    student_id: str
):

    reports = load_json(
        REPORT_FILE
    )

    if student_id not in reports:

        raise HTTPException(
            status_code=404,
            detail=f"学生不存在：{student_id}"
        )

    return reports[
        student_id
    ]


# ============================================================
# 获取全部学生综合报告
# ============================================================

@app.get("/api/reports")
def get_all_reports():

    reports = load_json(
        REPORT_FILE
    )

    return {
        "count": len(reports),
        "reports": reports
    }


# ============================================================
# 获取全部学习路径
# ============================================================

@app.get("/api/learning-paths")
def get_all_learning_paths():

    paths = load_json(
        PATH_FILE
    )

    return {
        "count": len(paths),
        "learning_paths": paths
    }