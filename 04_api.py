# -*- coding: utf-8 -*-

"""
04_api.py

学海智导 POC - FastAPI 后端

功能：

student_profiles.json
learning_paths.json
student_reports.json
        ↓
     FastAPI
        ↓
提供 REST API
        ↓
浏览器 / 前端可以访问

当前阶段：
1. 获取系统概况
2. 获取所有学生
3. 获取单个学生画像
4. 获取单个学生学习路径
5. 获取单个学生综合报告
6. 获取所有学生综合报告
"""

import json
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import assistant_service
import event_service
import quiz_service
import bkt_service
import bkt_state_service
import bkt_event_processor
from knowledge_graph_service import knowledge_graph_service


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
    description="学海智导——AI驱动的大学生个性化学习指导平台 POC",
    version="0.1.0"
)

# 配置 CORS 跨域支持
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["GET", "OPTIONS"],
    allow_headers=["*"],
)


# ============================================================
# JSON 读取工具
# ============================================================

def load_json(file_path):
    """
    读取 JSON 文件。
    """

    if not file_path.exists():
        raise FileNotFoundError(
            f"文件不存在：{file_path}"
        )

    with open(
        file_path,
        "r",
        encoding="utf-8"
    ) as f:

        return json.load(f)


# ============================================================
# 启动时检查数据文件
# ============================================================

print("=" * 70)
print("学海智导 · FastAPI 后端")
print("=" * 70)

print()
print("项目目录：", BASE_DIR)
print("数据目录：", OUTPUT_DIR)

print()
print("检查数据文件...")

for file_path in [
    PROFILE_FILE,
    PATH_FILE,
    REPORT_FILE
]:

    if file_path.exists():

        print(
            f"[OK] {file_path.name}"
        )

    else:

        print(
            f"[FAIL] {file_path.name} 不存在"
        )


# ============================================================
# 首页
# ============================================================

@app.get("/")
def root():

    return {
        "message": "学海智导 API 正常运行",
        "project": "学海智导",
        "version": "0.1.0",
        "docs": "/docs"
    }


# ============================================================
# 系统健康检查
# ============================================================

@app.get("/api/health")
def health_check():

    return {
        "status": "ok",
        "message": "学海智导后端服务运行正常"
    }


# ============================================================
# 系统概况
# ============================================================

@app.get("/api/overview")
def get_overview():

    profiles = load_json(
        PROFILE_FILE
    )

    paths = load_json(
        PATH_FILE
    )

    reports = load_json(
        REPORT_FILE
    )

    return {

        "student_count":
            len(profiles),

        "profile_count":
            len(profiles),

        "learning_path_count":
            len(paths),

        "report_count":
            len(reports),

        "students": [

            {
                "student_id":
                    student_id,

                "student_name":
                    profile.get(
                        "student",
                        {}
                    ).get(
                        "student_name",
                        ""
                    )
            }

            for student_id, profile
            in profiles.items()
        ]
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
                    "student_name",
                    ""
                ),

            "major":
                student.get(
                    "major",
                    ""
                ),

            "grade":
                student.get(
                    "grade",
                    ""
                ),

            "learning_goal":
                student.get(
                    "learning_goal",
                    ""
                ),

            "average_accuracy":
                overall.get(
                    "average_accuracy",
                    0
                ),

            "mastery_level":
                overall.get(
                    "mastery_level",
                    ""
                ),

            "activity_level":
                overall.get(
                    "activity_level",
                    ""
                ),

            "completion_level":
                overall.get(
                    "completion_level",
                    ""
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
            detail=f"找不到学生：{student_id}"
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
            detail=f"找不到学生：{student_id}"
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
            detail=f"找不到学生：{student_id}"
        )

    return reports[
        student_id
    ]


# ============================================================
# 获取所有学生综合报告
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
# 获取指定学生的完整学习档案
# ============================================================

@app.get("/api/students/{student_id}/dashboard")
def get_student_dashboard(
    student_id: str
):

    profiles = load_json(
        PROFILE_FILE
    )

    paths = load_json(
        PATH_FILE
    )

    reports = load_json(
        REPORT_FILE
    )

    if student_id not in profiles:

        raise HTTPException(
            status_code=404,
            detail=f"找不到学生：{student_id}"
        )

    return {

        "student_id":
            student_id,

        "profile":
            profiles.get(
                student_id
            ),

        "learning_path":
            paths.get(
                student_id
            ),

        "report":
            reports.get(
                student_id
            )
    }


# ============================================================
# 获取指定学生的 AI 知识图谱拓扑与学情联动数据
# ============================================================

@app.get("/api/students/{student_id}/knowledge-graph")
def get_student_knowledge_graph(
    student_id: str
):
    """
    获取指定学生的微观经济学知识图谱拓扑与学情联动数据
    包含全部 30 个知识点、前置依赖边、各知识点掌握状态与 AI 图谱洞察
    """
    profiles = load_json(
        PROFILE_FILE
    )

    if student_id not in profiles:
        raise HTTPException(
            status_code=404,
            detail=f"找不到学生：{student_id}"
        )

    return knowledge_graph_service.get_student_knowledge_graph(
        student_id
    )


# ============================================================
# AI 学习助手模型与接口
# ============================================================

class AssistantMessageRequest(BaseModel):
    message: str


@app.post("/api/students/{student_id}/assistant")
def chat_with_assistant(
    student_id: str,
    request: AssistantMessageRequest
):
    """
    AI 学习助手问答接口
    接收学生问题，根据真实多维学情生成上下文相关的智能诊断与指导
    """
    msg = request.message.strip() if request.message else ""
    if not msg:
        raise HTTPException(
            status_code=400,
            detail="消息内容不能为空"
        )

    profiles = load_json(PROFILE_FILE)
    if student_id not in profiles:
        raise HTTPException(
            status_code=404,
            detail=f"找不到学生：{student_id}"
        )

    response = assistant_service.generate_assistant_response(
        student_id=student_id,
        message=msg
    )
    return response


@app.get("/api/students/{student_id}/assistant/greeting")
def get_assistant_greeting(
    student_id: str
):
    """
    获取针对当前学生的 AI 首次专属问候语与动态快捷问题
    """
    profiles = load_json(PROFILE_FILE)
    if student_id not in profiles:
        raise HTTPException(
            status_code=404,
            detail=f"找不到学生：{student_id}"
        )

    return assistant_service.get_assistant_greeting(
        student_id=student_id
    )


# ============================================================
# 学习行为事件采集接口 (Learning Events)
# ============================================================

@app.post("/api/events", response_model=event_service.EventSubmissionResponse)
def submit_learning_event(event: event_service.LearningEventCreate):
    """
    统一接收并持久化来自前端、测验系统或伴学模块的学习行为事件
    """
    stored = event_service.record_event(event)
    return event_service.EventSubmissionResponse(
        status="success",
        event_id=stored.event_id,
        server_timestamp=stored.server_timestamp,
    )


# ============================================================
# 分知识点微测验接口 (Knowledge-Point Quizzes)
# ============================================================

@app.get("/api/quiz/{knowledge_id}", response_model=quiz_service.QuizKnowledgeListResponse)
def get_quiz_questions(knowledge_id: str):
    """
    按知识点查询测验题目（返回脱敏公开模型，严格剔除正确答案与解析）
    """
    return quiz_service.get_questions_by_knowledge_id(knowledge_id)


@app.post("/api/quiz/submit", response_model=quiz_service.QuizSubmitResponse)
def submit_quiz_answer(req: quiz_service.QuizSubmitRequest):
    """
    提交题目答案，服务端权威判题并自动记录 QUESTION_ATTEMPT 学习行为事件
    """
    return quiz_service.submit_quiz_answer(req)


# ============================================================
# 动态学情认知状态 (BKT Knowledge State) 接口
# ============================================================

class BKTStateResponse(BaseModel):
    student_id: str
    knowledge_id: str
    mastery_probability: float
    mastery_percent: float
    attempts: int
    correct_attempts: int
    incorrect_attempts: int
    consecutive_correct: int
    consecutive_incorrect: int
    last_updated: Optional[str] = None
    last_event_id: Optional[str] = None


class LearningStateUpdateRequest(BaseModel):
    event_id: str


class LearningStateUpdateResponse(BaseModel):
    status: str
    event_id: str
    student_id: Optional[str] = None
    knowledge_id: Optional[str] = None
    before: Optional[float] = None
    after: Optional[float] = None
    changed: bool = False
    reason: Optional[str] = None


@app.get(
    "/api/students/{student_id}/knowledge-state/{knowledge_id}",
    response_model=BKTStateResponse,
)
def get_student_knowledge_state(student_id: str, knowledge_id: str):
    """
    查询指定学生指定知识点的动态 BKT 掌握度认知状态
    若尚无作答记录，返回 P(L0)=0.20 的合法初始状态
    """
    profiles = load_json(PROFILE_FILE)
    if student_id not in profiles:
        raise HTTPException(
            status_code=404,
            detail=f"找不到学生：{student_id}",
        )

    if not quiz_service.is_valid_knowledge_id(knowledge_id):
        raise HTTPException(
            status_code=404,
            detail=f"未找到对应知识点：{knowledge_id}",
        )

    state = bkt_state_service.get_state(student_id, knowledge_id, auto_init=True)
    mastery_pct = round(state.mastery_probability * 100.0, 2)

    return BKTStateResponse(
        student_id=state.student_id,
        knowledge_id=state.knowledge_id,
        mastery_probability=round(state.mastery_probability, 6),
        mastery_percent=mastery_pct,
        attempts=state.attempts,
        correct_attempts=state.correct_attempts,
        incorrect_attempts=state.incorrect_attempts,
        consecutive_correct=state.consecutive_correct,
        consecutive_incorrect=state.consecutive_incorrect,
        last_updated=state.last_updated,
        last_event_id=state.last_event_id,
    )


@app.post(
    "/api/learning-state/update",
    response_model=LearningStateUpdateResponse,
)
def update_learning_state_from_event(req: LearningStateUpdateRequest):
    """
    根据已落盘的学习事件触发 BKT 认知状态演进（消费已有事件，幂等保证）
    """
    event = bkt_event_processor.find_event_by_id(req.event_id)
    if not event:
        raise HTTPException(
            status_code=404,
            detail=f"未找到对应学习事件：{req.event_id}",
        )

    result = bkt_event_processor.process_event(event)

    return LearningStateUpdateResponse(
        status=result.status,
        event_id=result.event_id,
        student_id=result.student_id,
        knowledge_id=result.knowledge_id,
        before=round(result.before_mastery, 6) if result.before_mastery is not None else None,
        after=round(result.after_mastery, 6) if result.after_mastery is not None else None,
        changed=result.changed,
        reason=result.reason,
    )


# ============================================================
# 启动提示
# ============================================================

if __name__ == "__main__":

    import uvicorn

    print()
    print("=" * 70)
    print("正在启动学海智导 API 服务...")
    print("=" * 70)

    print()
    print("API 地址：")
    print("http://127.0.0.1:8000")

    print()
    print("Swagger API 文档：")
    print("http://127.0.0.1:8000/docs")

    print()
    print("按 Ctrl + C 停止服务")
    print()

    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8000
    )