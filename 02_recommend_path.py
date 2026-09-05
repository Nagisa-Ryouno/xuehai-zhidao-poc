# -*- coding: utf-8 -*-
"""
02_recommend_path.py

学海智导 POC - 第二阶段

功能：

student_profiles.json
        +
knowledge_points
        ↓
知识点薄弱程度分析
        ↓
前置知识依赖分析
        ↓
学习优先级计算
        ↓
知识图谱路径排序
        ↓
个性化学习路径生成
        ↓
learning_paths.json
"""

import json
from pathlib import Path
from collections import defaultdict

import openpyxl


# ============================================================
# 配置
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

PROFILE_FILE = BASE_DIR / "output" / "student_profiles.json"
EXCEL_FILE = BASE_DIR / "economics_learning_demo.xlsx"

OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_FILE = OUTPUT_DIR / "learning_paths.json"


# ============================================================
# 工具函数
# ============================================================

def safe_float(value, default=0):
    """安全转换为 float"""
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def split_ids(value):
    """
    将：

    K01,K02

    转换为：

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


# ============================================================
# 程序开始
# ============================================================

print("=" * 70)
print("学海智导 · 个性化学习路径推荐引擎")
print("=" * 70)

print()
print("项目目录：", BASE_DIR)
print("画像文件：", PROFILE_FILE)
print("Excel文件：", EXCEL_FILE)


# ============================================================
# 检查文件
# ============================================================

if not PROFILE_FILE.exists():
    print()
    print("❌ 找不到 student_profiles.json")
    print("请先运行 01_prepare_data.py")
    raise SystemExit(1)

if not EXCEL_FILE.exists():
    print()
    print("❌ 找不到 economics_learning_demo.xlsx")
    print("请确认 Excel 文件和 Python 文件位于同一个目录")
    raise SystemExit(1)

print()
print("文件检查通过。")


# ============================================================
# 读取学生画像
# ============================================================

print()
print("正在读取学生画像...")

with open(
    PROFILE_FILE,
    "r",
    encoding="utf-8"
) as f:
    profiles = json.load(f)

print(f"成功读取 {len(profiles)} 名学生。")


# ============================================================
# 读取知识图谱
# ============================================================

print()
print("正在读取知识图谱...")

wb = openpyxl.load_workbook(
    EXCEL_FILE,
    data_only=True
)

if "knowledge_points" not in wb.sheetnames:
    print("❌ Excel 中不存在 knowledge_points 工作表")
    raise SystemExit(1)

ws = wb["knowledge_points"]

knowledge_points = {}

for row in ws.iter_rows(
    min_row=2,
    values_only=True
):

    (
        knowledge_id,
        knowledge_name,
        chapter,
        description,
        difficulty,
        prerequisite,
        next_knowledge
    ) = row

    if knowledge_id is None:
        continue

    knowledge_id = str(
        knowledge_id
    ).strip()

    knowledge_points[knowledge_id] = {
        "knowledge_id": knowledge_id,
        "knowledge_name": knowledge_name,
        "chapter": chapter,
        "description": description,
        "difficulty": safe_float(difficulty),
        "prerequisite": split_ids(prerequisite),
        "next_knowledge": split_ids(next_knowledge)
    }

print(
    f"成功读取 {len(knowledge_points)} 个知识点。"
)


# ============================================================
# 知识点辅助函数
# ============================================================

def get_knowledge(knowledge_id):
    """获取知识点信息"""

    return knowledge_points.get(
        knowledge_id,
        {
            "knowledge_id": knowledge_id,
            "knowledge_name": knowledge_id,
            "chapter": "",
            "description": "",
            "difficulty": 0,
            "prerequisite": [],
            "next_knowledge": []
        }
    )


# ============================================================
# 获取学生所有知识点掌握情况
# ============================================================

def build_mastery_map(profile):
    """
    从学生画像中建立：

    knowledge_id
        ↓
    accuracy

    方便后续判断前置知识是否已经掌握。
    """

    mastery = {}

    # 薄弱知识点
    for item in profile.get(
        "weak_knowledge_points",
        []
    ):

        knowledge_id = item.get(
            "knowledge_id"
        )

        if not knowledge_id:
            continue

        mastery[
            knowledge_id
        ] = safe_float(
            item.get("accuracy")
        )

    # 前置知识
    for item in profile.get(
        "prerequisite_knowledge_points",
        []
    ):

        knowledge_id = item.get(
            "knowledge_id"
        )

        if not knowledge_id:
            continue

        accuracy = item.get(
            "accuracy"
        )

        if accuracy is None:
            mastery[
                knowledge_id
            ] = None
        else:
            mastery[
                knowledge_id
            ] = safe_float(
                accuracy
            )

    return mastery


# ============================================================
# 递归获取所有前置知识
# ============================================================

def get_all_prerequisites(
    knowledge_id,
    max_depth=5
):
    """
    递归寻找知识点的所有前置知识。

    例如：

    K11
      ↓
    K08
      ↓
    K04

    最终：

    [K08, K04]
    """

    result = []
    visited = set()

    def dfs(
        current_id,
        depth
    ):

        if depth > max_depth:
            return

        if current_id in visited:
            return

        visited.add(current_id)

        kp = get_knowledge(
            current_id
        )

        for prerequisite_id in kp[
            "prerequisite"
        ]:

            if prerequisite_id not in result:

                result.append(
                    prerequisite_id
                )

            dfs(
                prerequisite_id,
                depth + 1
            )

    dfs(
        knowledge_id,
        1
    )

    return result


# ============================================================
# 计算依赖数量
# ============================================================

def calculate_dependency_counts(
    weak_points
):
    """
    计算：

    一个知识点
    被多少个薄弱知识点依赖。

    这个指标可以体现：

    “知识枢纽价值”
    """

    dependency_count = defaultdict(int)

    for weak in weak_points:

        weak_id = weak.get(
            "knowledge_id"
        )

        if not weak_id:
            continue

        prerequisites = get_all_prerequisites(
            weak_id
        )

        for prerequisite_id in prerequisites:

            dependency_count[
                prerequisite_id
            ] += 1

    return dict(
        dependency_count
    )


# ============================================================
# 计算学习优先级
# ============================================================

def calculate_priority_score(
    accuracy,
    difficulty,
    dependency_count,
    average_time,
    source
):
    """
    综合计算学习优先级。

    指标：

    1. 正确率越低
       → 优先级越高

    2. 被多个薄弱知识点依赖
       → 优先级越高

    3. 难度越高
       → 略微提高优先级

    4. 答题耗时越长
       → 优先级略微提高
    """

    # --------------------------------------------------------
    # 1. 薄弱程度
    # --------------------------------------------------------

    weakness_score = (
        max(
            0,
            100 - accuracy
        )
    )

    # --------------------------------------------------------
    # 2. 难度
    # --------------------------------------------------------

    difficulty_score = (
        difficulty * 4
    )

    # --------------------------------------------------------
    # 3. 知识依赖价值
    # --------------------------------------------------------

    dependency_score = min(
        dependency_count * 10,
        30
    )

    # --------------------------------------------------------
    # 4. 答题耗时
    # --------------------------------------------------------

    time_score = 0

    if average_time >= 180:

        time_score = 10

    elif average_time >= 150:

        time_score = 7

    elif average_time >= 100:

        time_score = 4

    # --------------------------------------------------------
    # 5. 来源加成
    # --------------------------------------------------------

    source_score = 0

    if source == "前置知识":

        source_score = 5

    # --------------------------------------------------------
    # 综合计算
    # --------------------------------------------------------

    score = (
        weakness_score * 0.60
        +
        difficulty_score * 0.10
        +
        dependency_score * 0.15
        +
        time_score * 0.10
        +
        source_score * 0.05
    )

    return round(
        score,
        2
    )


# ============================================================
# 根据正确率判断优先级
# ============================================================

def get_priority(
    accuracy,
    priority_score
):
    """
    最终优先级。

    正确率是最核心指标，
    priority_score 用于辅助判断。
    """

    # 明显薄弱
    if accuracy < 50:

        return "高"

    # 中度薄弱
    if accuracy < 70:

        return "中"

    # 如果正确率已经达到70%以上，
    # 但依赖价值非常高，
    # 仍然可以作为巩固内容

    if priority_score >= 45:

        return "中"

    return "低"


# ============================================================
# 生成推荐原因
# ============================================================

def build_reason(
    item,
    dependency_count
):

    accuracy = item[
        "accuracy"
    ]

    reasons = []

    # 正确率
    if accuracy < 50:

        reasons.append(
            f"当前正确率仅{accuracy:.0f}%，属于明显薄弱知识点"
        )

    elif accuracy < 70:

        reasons.append(
            f"当前正确率为{accuracy:.0f}%，掌握程度仍需加强"
        )

    else:

        reasons.append(
            f"当前正确率为{accuracy:.0f}%，基础掌握较好"
        )

    # 前置知识
    if dependency_count > 0:

        reasons.append(
            f"该知识点是其他{dependency_count}个相关薄弱知识点的前置知识"
        )

    # 时间
    if item[
        "average_time_seconds"
    ] >= 150:

        reasons.append(
            "当前答题耗时较长，建议增加限时训练"
        )

    return "；".join(
        reasons
    )


# ============================================================
# 对知识点进行拓扑排序
# ============================================================

def order_by_dependency(
    recommendations
):
    """
    根据知识依赖关系进行排序。

    核心原则：

    前置知识
        ↓
    后续知识

    例如：

    预算约束线
        ↓
    无差异曲线
        ↓
    消费者最优选择
    """

    recommendation_map = {
        item["knowledge_id"]: item
        for item in recommendations
    }

    # --------------------------------------------------------
    # 建立依赖图
    # --------------------------------------------------------

    graph = defaultdict(list)

    indegree = {
        item["knowledge_id"]: 0
        for item in recommendations
    }

    for item in recommendations:

        knowledge_id = item[
            "knowledge_id"
        ]

        kp = get_knowledge(
            knowledge_id
        )

        for prerequisite_id in kp[
            "prerequisite"
        ]:

            if prerequisite_id in indegree:

                graph[
                    prerequisite_id
                ].append(
                    knowledge_id
                )

                indegree[
                    knowledge_id
                ] += 1

    # --------------------------------------------------------
    # 初始节点
    # --------------------------------------------------------

    queue = [
        knowledge_id
        for knowledge_id, degree
        in indegree.items()
        if degree == 0
    ]

    # 高优先级优先
    queue.sort(
        key=lambda kid:
        recommendation_map[
            kid
        ]["priority_score"],
        reverse=True
    )

    ordered = []

    # --------------------------------------------------------
    # 拓扑排序
    # --------------------------------------------------------

    while queue:

        current_id = queue.pop(0)

        ordered.append(
            recommendation_map[
                current_id
            ]
        )

        for next_id in graph[
            current_id
        ]:

            indegree[
                next_id
            ] -= 1

            if indegree[
                next_id
            ] == 0:

                queue.append(
                    next_id
                )

                queue.sort(
                    key=lambda kid:
                    recommendation_map[
                        kid
                    ]["priority_score"],
                    reverse=True
                )

    # --------------------------------------------------------
    # 防止知识图谱存在环
    # --------------------------------------------------------

    if len(ordered) < len(
        recommendations
    ):

        remaining = [
            item
            for item in recommendations
            if item not in ordered
        ]

        remaining.sort(
            key=lambda x:
            x["priority_score"],
            reverse=True
        )

        ordered.extend(
            remaining
        )

    return ordered


# ============================================================
# 分析单个学生
# ============================================================

def recommend_for_student(
    student_id,
    profile
):

    student = profile.get(
        "student",
        {}
    )

    overall = profile.get(
        "overall_profile",
        {}
    )

    weak_points = profile.get(
        "weak_knowledge_points",
        []
    )

    prerequisite_points = profile.get(
        "prerequisite_knowledge_points",
        []
    )

    # --------------------------------------------------------
    # 基础指标
    # --------------------------------------------------------

    avg_accuracy = safe_float(
        overall.get(
            "average_accuracy"
        )
    )

    speed_status = overall.get(
        "speed_status",
        ""
    )

    activity_level = overall.get(
        "activity_level",
        ""
    )

    completion_level = overall.get(
        "completion_level",
        ""
    )

    # --------------------------------------------------------
    # 如果没有薄弱知识点
    # --------------------------------------------------------

    if not weak_points:

        optimization_suggestions = [
            "当前知识掌握程度较好，建议减少基础重复训练。",
            "建议增加综合应用题、跨知识点训练和限时模拟。",
            "可逐步挑战更高难度知识点，提升知识迁移能力。"
        ]

        return {

            "student": student,

            "profile_summary": {

                "mastery_level":
                    overall.get(
                        "mastery_level"
                    ),

                "average_accuracy":
                    avg_accuracy,

                "average_assessment_score":
                    overall.get(
                        "average_assessment_score"
                    ),

                "speed_status":
                    speed_status,

                "activity_level":
                    activity_level,

                "completion_level":
                    completion_level
            },

            "recommendation_type":
                "综合能力提升",

            "learning_path": [],

            "optimization_suggestion":
                optimization_suggestions
        }

    # --------------------------------------------------------
    # 建立掌握情况
    # --------------------------------------------------------

    mastery = build_mastery_map(
        profile
    )

    # --------------------------------------------------------
    # 计算知识依赖关系
    # --------------------------------------------------------

    dependency_counts = calculate_dependency_counts(
        weak_points
    )

    # --------------------------------------------------------
    # 建立候选知识点
    # --------------------------------------------------------

    candidates = {}

    # ========================================================
    # 第一类：直接薄弱知识点
    # ========================================================

    for weak in weak_points:

        knowledge_id = weak.get(
            "knowledge_id"
        )

        if not knowledge_id:
            continue

        kp = get_knowledge(
            knowledge_id
        )

        candidates[
            knowledge_id
        ] = {

            "knowledge_id":
                knowledge_id,

            "knowledge_name":
                weak.get(
                    "knowledge_name",
                    kp["knowledge_name"]
                ),

            "chapter":
                kp["chapter"],

            "difficulty":
                safe_float(
                    weak.get(
                        "difficulty",
                        kp["difficulty"]
                    )
                ),

            "accuracy":
                safe_float(
                    weak.get(
                        "accuracy"
                    )
                ),

            "assessment_score":
                safe_float(
                    weak.get(
                        "assessment_score"
                    )
                ),

            "average_time_seconds":
                safe_float(
                    weak.get(
                        "average_time_seconds"
                    )
                ),

            "source":
                "薄弱知识点"
        }

    # ========================================================
    # 第二类：前置知识
    # ========================================================

    for prerequisite in prerequisite_points:

        knowledge_id = prerequisite.get(
            "knowledge_id"
        )

        if not knowledge_id:
            continue

        if knowledge_id in candidates:
            continue

        kp = get_knowledge(
            knowledge_id
        )

        accuracy = prerequisite.get(
            "accuracy"
        )

        # 没有学习记录
        if accuracy is None:

            # 不把未知情况直接当成70分参与排序
            # 而是给一个中性值
            accuracy = 50

        candidates[
            knowledge_id
        ] = {

            "knowledge_id":
                knowledge_id,

            "knowledge_name":
                prerequisite.get(
                    "knowledge_name",
                    kp["knowledge_name"]
                ),

            "chapter":
                kp["chapter"],

            "difficulty":
                safe_float(
                    kp["difficulty"]
                ),

            "accuracy":
                safe_float(
                    accuracy
                ),

            "assessment_score":
                None,

            "average_time_seconds":
                0,

            "source":
                "前置知识"
        }

    # --------------------------------------------------------
    # 计算推荐信息
    # --------------------------------------------------------

    recommendations = []

    for knowledge_id, item in candidates.items():

        dependency_count = (
            dependency_counts.get(
                knowledge_id,
                0
            )
        )

        priority_score = calculate_priority_score(

            accuracy=item[
                "accuracy"
            ],

            difficulty=item[
                "difficulty"
            ],

            dependency_count=
                dependency_count,

            average_time=
                item[
                    "average_time_seconds"
                ],

            source=item[
                "source"
            ]
        )

        priority = get_priority(
            item["accuracy"],
            priority_score
        )

        reason = build_reason(
            item,
            dependency_count
        )

        recommendations.append({

            "knowledge_id":
                knowledge_id,

            "knowledge_name":
                item[
                    "knowledge_name"
                ],

            "chapter":
                item[
                    "chapter"
                ],

            "difficulty":
                item[
                    "difficulty"
                ],

            "current_accuracy":
                item[
                    "accuracy"
                ],

            "priority":
                priority,

            "priority_score":
                priority_score,

            "source":
                item[
                    "source"
                ],

            "dependency_count":
                dependency_count,

            "reason":
                reason
        })

    # --------------------------------------------------------
    # 按知识依赖关系排序
    # --------------------------------------------------------

    recommendations = order_by_dependency(
        recommendations
    )

    # --------------------------------------------------------
    # 生成学习路径
    # --------------------------------------------------------

    learning_path = []

    for stage, item in enumerate(
        recommendations[:8],
        start=1
    ):

        accuracy = item[
            "current_accuracy"
        ]

        if item[
            "source"
        ] == "前置知识":

            learning_goal = (
                "补齐前置知识基础"
            )

        elif accuracy < 50:

            learning_goal = (
                "优先修复知识薄弱点"
            )

        elif accuracy < 70:

            learning_goal = (
                "强化知识理解与解题能力"
            )

        else:

            learning_goal = (
                "巩固知识并提升综合应用能力"
            )

        learning_path.append({

            "stage":
                stage,

            "knowledge_id":
                item[
                    "knowledge_id"
                ],

            "knowledge_name":
                item[
                    "knowledge_name"
                ],

            "chapter":
                item[
                    "chapter"
                ],

            "current_accuracy":
                accuracy,

            "priority":
                item[
                    "priority"
                ],

            "priority_score":
                item[
                    "priority_score"
                ],

            "source":
                item[
                    "source"
                ],

            "learning_goal":
                learning_goal,

            "reason":
                item[
                    "reason"
                ]
        })

    # --------------------------------------------------------
    # 推荐策略
    # --------------------------------------------------------

    if avg_accuracy < 60:

        recommendation_type = (
            "基础补强"
        )

    elif (
        speed_status ==
        "答题耗时较长"
    ):

        recommendation_type = (
            "能力巩固 + 限时训练"
        )

    elif (
        activity_level == "高"
        and avg_accuracy < 70
    ):

        recommendation_type = (
            "高参与度转化训练"
        )

    else:

        recommendation_type = (
            "薄弱知识点强化"
        )

    # --------------------------------------------------------
    # 优化建议
    # --------------------------------------------------------

    optimization_suggestions = []

    if avg_accuracy < 60:

        optimization_suggestions.append(
            "当前整体掌握程度较弱，建议优先补齐基础知识和前置知识。"
        )

    elif avg_accuracy >= 80:

        optimization_suggestions.append(
            "当前整体掌握程度较好，不建议大量重复基础内容，可增加综合应用训练。"
        )

    if speed_status == "答题耗时较长":

        optimization_suggestions.append(
            "正确率较高但答题耗时较长，建议加入限时练习和模拟测试。"
        )

    if (
        activity_level == "高"
        and avg_accuracy < 70
    ):

        optimization_suggestions.append(
            "学习参与度较高但正确率仍有限，应重点加强错题复盘和知识理解。"
        )

    if completion_level == "较低":

        optimization_suggestions.append(
            "当前学习完成度偏低，建议减少单次学习任务量，提高学习计划完成率。"
        )

    if not optimization_suggestions:

        optimization_suggestions.append(
            "建议根据本轮学习效果持续调整学习路径。"
        )

    # --------------------------------------------------------
    # 最终返回
    # --------------------------------------------------------

    return {

        "student":
            student,

        "profile_summary": {

            "mastery_level":
                overall.get(
                    "mastery_level"
                ),

            "average_accuracy":
                avg_accuracy,

            "average_assessment_score":
                overall.get(
                    "average_assessment_score"
                ),

            "speed_status":
                speed_status,

            "activity_level":
                activity_level,

            "completion_level":
                completion_level
        },

        "recommendation_type":
            recommendation_type,

        "learning_path":
            learning_path,

        "optimization_suggestion":
            optimization_suggestions
    }


# ============================================================
# 为所有学生生成学习路径
# ============================================================

print()
print("=" * 70)
print("开始生成个性化学习路径")
print("=" * 70)

learning_paths = {}

for student_id, profile in profiles.items():

    print()
    print(
        f"正在分析 {student_id}..."
    )

    result = recommend_for_student(
        student_id,
        profile
    )

    learning_paths[
        student_id
    ] = result

    print(
        f"推荐策略："
        f"{result['recommendation_type']}"
    )

    print(
        "学习路径："
    )

    if not result[
        "learning_path"
    ]:

        print(
            "  （暂无需要优先补强的知识点）"
        )

    else:

        for item in result[
            "learning_path"
        ]:

            print(
                f"  {item['stage']}. "
                f"{item['knowledge_name']} "
                f"(正确率："
                f"{item['current_accuracy']:.0f}%"
                f"，优先级："
                f"{item['priority']})"
            )


# ============================================================
# 保存 JSON
# ============================================================

OUTPUT_DIR.mkdir(
    exist_ok=True
)

with open(
    OUTPUT_FILE,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        learning_paths,
        f,
        ensure_ascii=False,
        indent=2
    )


# ============================================================
# 输出最终总结
# ============================================================

print()
print("=" * 70)
print("个性化学习路径生成完成！")
print("=" * 70)

print(
    f"学生数量："
    f"{len(learning_paths)}"
)

print(
    f"输出文件："
    f"{OUTPUT_FILE}"
)

print()

for student_id, result in learning_paths.items():

    student = result[
        "student"
    ]

    print(
        f"【{student_id} "
        f"{student.get('student_name', '')}】"
    )

    print(
        f"推荐策略："
        f"{result['recommendation_type']}"
    )

    print(
        "学习路径："
    )

    if not result[
        "learning_path"
    ]:

        print(
            "  → 暂无需要优先补强的知识点"
        )

    else:

        for item in result[
            "learning_path"
        ]:

            print(
                f"  → "
                f"{item['knowledge_name']}"
                f"（{item['priority']}）"
            )

    print(
        "优化建议："
    )

    for suggestion in result[
        "optimization_suggestion"
    ]:

        print(
            f"  • {suggestion}"
        )

    print()