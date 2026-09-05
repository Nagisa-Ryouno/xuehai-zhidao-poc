# -*- coding: utf-8 -*-
"""
01_prepare_data.py

功能：
Excel学习数据
    ↓
Python数据分析
    ↓
生成学生多维学情画像
    ↓
student_profiles.json
"""

import json
import os
from collections import defaultdict
from pathlib import Path

import openpyxl


# =========================
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.core.config import settings

BASE_DIR = settings.PROJECT_ROOT

# Excel 数据文件
EXCEL_PATH = settings.EXCEL_RAW_FILE if settings.EXCEL_RAW_FILE.exists() else BASE_DIR / "economics_learning_demo.xlsx"

# 输出目录
OUTPUT_DIR = settings.SEEDS_DIR
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# 输出 JSON
OUTPUT_FILE = settings.STUDENT_PROFILES_FILE


# =========================
# 工具函数
# =========================

def safe_float(value, default=0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def safe_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def split_ids(value):
    """
    将：
    K01,K02
    转换成：
    ["K01", "K02"]
    """
    if value is None:
        return []

    value = str(value).strip()

    if not value or value.upper() == "NULL":
        return []

    return [
        item.strip()
        for item in value.split(",")
        if item.strip()
    ]


# =========================
# 读取Excel
# =========================

print("正在读取 Excel...")

wb = openpyxl.load_workbook(EXCEL_PATH, data_only=True)

ws_kp = wb["knowledge_points"]
ws_students = wb["students"]
ws_records = wb["learning_records"]
ws_assessments = wb["assessment_rounds"]


# =========================
# 读取知识点
# =========================

knowledge_points = {}

for row in ws_kp.iter_rows(min_row=2, values_only=True):
    (
        knowledge_id,
        knowledge_name,
        chapter,
        description,
        difficulty,
        prerequisite,
        next_knowledge
    ) = row

    knowledge_points[str(knowledge_id)] = {
        "knowledge_id": str(knowledge_id),
        "knowledge_name": knowledge_name,
        "chapter": chapter,
        "description": description,
        "difficulty": safe_int(difficulty),
        "prerequisite": split_ids(prerequisite),
        "next_knowledge": split_ids(next_knowledge)
    }


# =========================
# 读取学生
# =========================

students = {}

for row in ws_students.iter_rows(min_row=2, values_only=True):
    (
        student_id,
        student_name,
        major,
        grade,
        learning_goal
    ) = row

    students[str(student_id)] = {
        "student_id": str(student_id),
        "student_name": student_name,
        "major": major,
        "grade": grade,
        "learning_goal": learning_goal
    }


# =========================
# 读取学习记录
# =========================

student_records = defaultdict(list)

for row in ws_records.iter_rows(min_row=2, values_only=True):

    (
        record_id,
        student_id,
        knowledge_id,
        accuracy,
        average_time_seconds,
        practice_count,
        mistake_count,
        learning_duration_minutes,
        interaction_count,
        completion_rate,
        assessment_score
    ) = row

    student_id = str(student_id)
    knowledge_id = str(knowledge_id)

    record = {
        "record_id": record_id,
        "student_id": student_id,
        "knowledge_id": knowledge_id,
        "knowledge_name": knowledge_points.get(
            knowledge_id,
            {}
        ).get("knowledge_name", knowledge_id),

        "accuracy": safe_float(accuracy),
        "average_time_seconds": safe_float(average_time_seconds),
        "practice_count": safe_int(practice_count),
        "mistake_count": safe_int(mistake_count),
        "learning_duration_minutes": safe_float(
            learning_duration_minutes
        ),
        "interaction_count": safe_int(interaction_count),
        "completion_rate": safe_float(completion_rate),
        "assessment_score": safe_float(assessment_score)
    }

    student_records[student_id].append(record)


# =========================
# 学情分析
# =========================

def analyze_student(student_id):

    student = students[student_id]
    records = student_records.get(student_id, [])

    if not records:
        return None

    # -------------------------
    # 基础统计
    # -------------------------

    total_accuracy = sum(
        r["accuracy"] for r in records
    ) / len(records)

    total_assessment = sum(
        r["assessment_score"] for r in records
    ) / len(records)

    total_learning_time = sum(
        r["learning_duration_minutes"]
        for r in records
    )

    total_practice = sum(
        r["practice_count"]
        for r in records
    )

    total_interaction = sum(
        r["interaction_count"]
        for r in records
    )

    avg_completion = sum(
        r["completion_rate"]
        for r in records
    ) / len(records)

    avg_time = sum(
        r["average_time_seconds"]
        for r in records
    ) / len(records)


    # -------------------------
    # 找出薄弱知识点
    # -------------------------

    weak_points = []

    for r in records:

        accuracy = r["accuracy"]

        if accuracy < 60:

            kp = knowledge_points.get(
                r["knowledge_id"],
                {}
            )

            weak_points.append({
                "knowledge_id": r["knowledge_id"],
                "knowledge_name": r["knowledge_name"],
                "accuracy": accuracy,
                "assessment_score": r["assessment_score"],
                "average_time_seconds": r[
                    "average_time_seconds"
                ],
                "difficulty": kp.get("difficulty", 0),
                "prerequisite": kp.get(
                    "prerequisite",
                    []
                )
            })


    # 按正确率从低到高排序

    weak_points.sort(
        key=lambda x: x["accuracy"]
    )


    # -------------------------
    # 找出需要优先补习的前置知识
    # -------------------------

    prerequisite_points = []

    weak_ids = {
        item["knowledge_id"]
        for item in weak_points
    }

    for weak in weak_points:

        for prerequisite_id in weak["prerequisite"]:

            if prerequisite_id in knowledge_points:

                prerequisite_record = next(
                    (
                        r for r in records
                        if r["knowledge_id"]
                        == prerequisite_id
                    ),
                    None
                )

                if prerequisite_record:

                    if prerequisite_record["accuracy"] < 70:

                        prerequisite_points.append({
                            "knowledge_id":
                                prerequisite_id,

                            "knowledge_name":
                                knowledge_points[
                                    prerequisite_id
                                ]["knowledge_name"],

                            "accuracy":
                                prerequisite_record[
                                    "accuracy"
                                ],

                            "reason":
                                f"该知识点是薄弱知识点"
                                f"{weak['knowledge_name']}"
                                f"的前置知识"
                        })

                else:

                    prerequisite_points.append({
                        "knowledge_id":
                            prerequisite_id,

                        "knowledge_name":
                            knowledge_points[
                                prerequisite_id
                            ]["knowledge_name"],

                        "accuracy":
                            None,

                        "reason":
                            f"该知识点是薄弱知识点"
                            f"{weak['knowledge_name']}"
                            f"的前置知识，但当前学习记录不足"
                    })


    # 去重

    unique_prerequisites = {}

    for item in prerequisite_points:
        unique_prerequisites[
            item["knowledge_id"]
        ] = item

    prerequisite_points = list(
        unique_prerequisites.values()
    )


    # -------------------------
    # 学习效率分析
    # -------------------------

    if total_accuracy >= 85:
        mastery_level = "较好"
    elif total_accuracy >= 70:
        mastery_level = "中等"
    elif total_accuracy >= 60:
        mastery_level = "偏弱"
    else:
        mastery_level = "较弱"


    # -------------------------
    # 学习速度分析
    # -------------------------

    if avg_time >= 150:
        speed_status = "答题耗时较长"
    elif avg_time >= 100:
        speed_status = "答题速度一般"
    else:
        speed_status = "答题速度较快"


    # -------------------------
    # 活跃度分析
    # -------------------------

    if total_interaction >= 300:
        activity_level = "高"
    elif total_interaction >= 150:
        activity_level = "中"
    else:
        activity_level = "低"


    # -------------------------
    # 学习完成度
    # -------------------------

    if avg_completion >= 90:
        completion_level = "高"
    elif avg_completion >= 75:
        completion_level = "中"
    else:
        completion_level = "较低"


    # -------------------------
    # 自动生成诊断结论
    # -------------------------

    diagnosis = []

    if total_accuracy < 60:
        diagnosis.append(
            "整体知识掌握程度偏弱，需要优先夯实基础"
        )
    elif total_accuracy < 75:
        diagnosis.append(
            "整体知识掌握程度一般，需要针对薄弱知识点进行强化"
        )
    else:
        diagnosis.append(
            "整体知识掌握程度较好，可进一步进行重点突破"
        )


    if weak_points:
        diagnosis.append(
            "存在多个知识薄弱点，需要进行针对性学习"
        )


    if prerequisite_points:
        diagnosis.append(
            "部分薄弱知识点可能与前置知识掌握不足有关，建议优先补齐知识链"
        )


    if avg_time >= 150:
        diagnosis.append(
            "答题正确率较高但耗时较长，需要加强限时训练"
        )


    if activity_level == "低":
        diagnosis.append(
            "学习互动活跃度较低，需要提高学习参与度"
        )


    if activity_level == "高" and total_accuracy < 70:
        diagnosis.append(
            "学习参与度较高但知识掌握仍有限，需要提高学习行为向学习效果的转化"
        )


    # -------------------------
    # 最终画像
    # -------------------------

    return {

        "student": student,

        "overall_profile": {

            "average_accuracy":
                round(total_accuracy, 2),

            "average_assessment_score":
                round(total_assessment, 2),

            "total_learning_time_minutes":
                round(total_learning_time, 2),

            "total_practice_count":
                total_practice,

            "total_interaction_count":
                total_interaction,

            "average_completion_rate":
                round(avg_completion, 2),

            "average_answer_time_seconds":
                round(avg_time, 2),

            "mastery_level":
                mastery_level,

            "speed_status":
                speed_status,

            "activity_level":
                activity_level,

            "completion_level":
                completion_level
        },

        "weak_knowledge_points":
            weak_points,

        "prerequisite_knowledge_points":
            prerequisite_points,

        "diagnosis":
            diagnosis
    }


# =========================
# 生成所有学生画像
# =========================

profiles = {}

for student_id in students:

    print(f"正在分析 {student_id}...")

    profile = analyze_student(student_id)

    if profile:
        profiles[student_id] = profile


# =========================
# 保存JSON
# =========================

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

with open(
    OUTPUT_FILE,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        profiles,
        f,
        ensure_ascii=False,
        indent=2
    )


print()
print("=" * 60)
print("学情分析完成！")
print("=" * 60)
print(f"学生数量：{len(profiles)}")
print(f"输出文件：{OUTPUT_FILE}")

for student_id, profile in profiles.items():

    print()
    print(
        f"{student_id} "
        f"{profile['student']['student_name']}"
    )

    print(
        "平均正确率：",
        profile["overall_profile"][
            "average_accuracy"
        ]
    )

    print(
        "掌握程度：",
        profile["overall_profile"][
            "mastery_level"
        ]
    )

    print(
        "薄弱知识点：",
        [
            x["knowledge_name"]
            for x in profile[
                "weak_knowledge_points"
            ]
        ]
    )