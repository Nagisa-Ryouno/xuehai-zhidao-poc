# -*- coding: utf-8 -*-
"""
gateway.api
学海智导 (Xuehai Zhidao) V2 - Phase 3 / Sprint 7-D
Stage F: Backend Secure AI Gateway 核心服务入口与生产加固可观测层

特性加固：
1. Request Correlation: 每个请求分配安全无害的 request_id (X-Request-ID Header 贯通)
2. Latency Observation: 毫秒级性能测量，仅作为元数据存在
3. Failure Taxonomy: 内部精细故障分类，面向学生文案彻底隔离
4. Fail-Safe Observability: 旁路审计与指标发生任何异常均被隔离，绝对不影响业务主流程
5. Security Redaction: 所有异常日志与追踪经过安全脱敏，严禁泄露密钥、内部路径与端点
"""

import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from fastapi import FastAPI, HTTPException, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.core.constants import PathState
import path_state_service
from app.services.knowledge_graph_service import knowledge_graph_service
from app.services.quiz_service import (
    QuizSubmitRequest,
    QuizSubmitResponse,
    QuizKnowledgeListResponse,
    QuizQuestionPublic,
    QuizOption,
    LearningStateSnapshot,
    get_mastery_state,
)
from app.infrastructure.persistence.event_repository import (
    LearningEventCreate,
    default_event_repository,
)
import bkt_event_processor
from app.services.path_replanning_service import evaluate_and_replan
from app.main import app as app_main

from gateway.content import (
    get_concept_card,
    get_all_concept_cards,
    get_public_questions_by_knowledge_id,
    get_question_by_id as get_content_question_by_id,
    ALL_QUIZ_QUESTIONS,
)
from gateway.adapter import (
    ProviderException,
    ProviderTimeoutError,
    execute_provider_with_timeout,
    get_provider,
)
from gateway.audit import (
    AuditEvent,
    ProviderFailureClass,
    generate_request_id,
    safe_increment_metric,
    safe_record_audit,
    METRIC_REQUESTS_TOTAL,
    METRIC_FAILURES_TOTAL,
    METRIC_FALLBACK_TOTAL,
    METRIC_TIMEOUT_TOTAL,
    METRIC_POLICY_VIOLATIONS_TOTAL,
)
from gateway.config import gateway_settings
from gateway.models import (
    AICompanionRequest,
    StructuredAIResponse,
)
from gateway.redaction import sanitize_exception_message

logger = logging.getLogger("xuehai.gateway")


def classify_provider_exception(exc: Exception) -> ProviderFailureClass:
    """内部故障分类映射函数"""
    msg = str(exc)
    if "forbidden decision field" in msg:
        return ProviderFailureClass.PROVIDER_POLICY_VIOLATION
    if "missing API key" in msg or "not configured" in msg:
        return ProviderFailureClass.PROVIDER_CONFIGURATION_ERROR
    if "client error (HTTP 4" in msg:
        return ProviderFailureClass.PROVIDER_BAD_RESPONSE
    if "server error (HTTP 5" in msg:
        return ProviderFailureClass.PROVIDER_UNAVAILABLE
    if "Connection refused" in msg or "connection" in msg.lower() or "network" in msg.lower():
        return ProviderFailureClass.NETWORK_FAILURE
    if "Invalid response" in msg or "missing required" in msg:
        return ProviderFailureClass.PROVIDER_BAD_RESPONSE
    return ProviderFailureClass.PROVIDER_UNAVAILABLE


class StudentInitRequest(BaseModel):
    student_id: Optional[str] = Field(default=None, description="自定义学生ID，为空时自动生成")
    student_name: str = Field(..., min_length=1, max_length=50, description="学生姓名")
    major: str = Field(default="经济学", description="所学专业")
    grade: str = Field(default="大二", description="年级")
    learning_goal: str = Field(default="微观经济学期末冲刺", description="阶段学习目标")
    class_name: Optional[str] = Field(default="经济学 2401班", description="班级")
    start_knowledge_id: str = Field(default="K01", description="初始聚焦考点")


class StudentInitResponse(BaseModel):
    student_id: str
    student_name: str
    major: str
    grade: str
    learning_goal: str
    class_name: str
    current_knowledge_id: str
    path_states: Dict[str, str]
    message: str


# 动态初始化的 Demo 学生档案注册表（内存态，支持测试与体验会话）
DEMO_STUDENTS: Dict[str, Dict[str, Any]] = {}


def create_gateway_app() -> FastAPI:
    """构建独立 AI Gateway FastAPI 应用实例"""
    application = FastAPI(
        title="学海智导 AI Gateway",
        description="Secure AI Gateway Boundary for Xuehai Zhidao",
        version="0.2.0",
        docs_url=None,  # 关闭内部文档探测
        redoc_url=None,
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @application.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ):
        """请求格式/白名单校验失败处理器，杜绝敏感堆栈泄露"""
        req_id = generate_request_id()
        safe_increment_metric(METRIC_FAILURES_TOTAL)
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content={
                "error": "SCHEMA_VALIDATION_FAILED",
                "detail": "请求载荷不符合网关安全白名单契约，已拒绝处理。",
                "errors": [
                    {"loc": [str(x) for x in err.get("loc", [])], "msg": err.get("msg", "")}
                    for err in exc.errors()
                ],
            },
            headers={"X-Request-ID": req_id},
        )

    @application.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception):
        """全局异常熔断：捕获所有未知异常，杜绝 Python Traceback 泄露给客户端"""
        req_id = generate_request_id()
        clean_name = sanitize_exception_message(exc.__class__.__name__)
        logger.error(f"Gateway internal exception [{req_id}]: {clean_name}")
        safe_increment_metric(METRIC_FAILURES_TOTAL)

        # 记录内部未捕获严重异常事件
        safe_record_audit(
            AuditEvent(
                event_name="GATEWAY_CRASHED",
                request_id=req_id,
                provider="unknown",
                model=gateway_settings.model,
                status="FAILED",
                failure_class=ProviderFailureClass.GATEWAY_INTERNAL_ERROR.value,
                fallback_used=True,
            )
        )

        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "GATEWAY_INTERNAL_ERROR",
                "detail": "网关服务异常，已触发安全降级熔断。",
                "grounding_status": "insufficient_context",
                "answer": "抱歉，伴学网关暂时出现内部异常，请稍后重试。",
            },
            headers={"X-Request-ID": req_id},
        )

    @application.get("/api/ai/health")
    def health_check() -> Dict[str, Any]:
        """网关健康检查探针"""
        return {
            "status": "healthy",
            "provider": gateway_settings.provider,
            "masked_key": gateway_settings.get_masked_api_key(),
            "timeout_ms": gateway_settings.timeout_ms,
        }

    @application.post(
        "/api/ai/companion",
        response_model=StructuredAIResponse,
        response_model_exclude_unset=True,
    )
    async def companion_endpoint(
        request: AICompanionRequest,
        response: Response,
    ) -> StructuredAIResponse:
        """
        AI 伴学主入口端点
        
        加固执行边界：
        1. Request Correlation: 注入 X-Request-ID Header 保证链路追踪
        2. Latency & Observability: 旁路收集耗时与状态事件，Fail-safe 熔断保护
        3. Request Validation: Pydantic 严格白名单校验 (extra='forbid')
        4. Provider Selection & Invocation: 委托给 AIProviderAdapter 抽象层
        5. Response Normalization: 仅返回 StructuredAIResponse 契约字段
        6. Secret & Authority Isolation: 密钥绝不暴露，决策权绝对隔离
        """
        request_id = generate_request_id()
        response.headers["X-Request-ID"] = request_id
        start_perf = time.perf_counter()

        prompt_context = request.prompt_context
        if request.question and request.question != prompt_context.user_question:
            prompt_context = prompt_context.model_copy(update={"user_question": request.question})

        provider = get_provider()

        # 1. 记录请求启动审计事件与指标递增
        safe_record_audit(
            AuditEvent(
                event_name="REQUEST_STARTED",
                request_id=request_id,
                provider=provider.provider_name,
                model=gateway_settings.model,
                status="STARTED",
            )
        )
        safe_increment_metric(METRIC_REQUESTS_TOTAL)

        # 2. 执行模型生成
        try:
            result = await execute_provider_with_timeout(
                provider,
                prompt_context,
                timeout_ms=gateway_settings.timeout_ms,
            )
            latency_ms = round((time.perf_counter() - start_perf) * 1000, 2)

            # 3. 正常完成审计事件记录
            safe_record_audit(
                AuditEvent(
                    event_name="PROVIDER_COMPLETED",
                    request_id=request_id,
                    provider=provider.provider_name,
                    model=gateway_settings.model,
                    status="SUCCESS",
                )
            )
            safe_record_audit(
                AuditEvent(
                    event_name="REQUEST_COMPLETED",
                    request_id=request_id,
                    provider=provider.provider_name,
                    model=gateway_settings.model,
                    status="SUCCESS",
                    latency_ms=latency_ms,
                )
            )
            return result

        except ProviderTimeoutError as e:
            latency_ms = round((time.perf_counter() - start_perf) * 1000, 2)
            clean_err = sanitize_exception_message(e)
            logger.warning(f"Gateway timeout [{request_id}]: {clean_err}")

            failure_class = ProviderFailureClass.PROVIDER_TIMEOUT.value
            safe_record_audit(
                AuditEvent(
                    event_name="PROVIDER_FAILED",
                    request_id=request_id,
                    provider=provider.provider_name,
                    model=gateway_settings.model,
                    status="FAILED",
                    failure_class=failure_class,
                    latency_ms=latency_ms,
                )
            )
            safe_record_audit(
                AuditEvent(
                    event_name="FALLBACK_ACTIVATED",
                    request_id=request_id,
                    provider=provider.provider_name,
                    model=gateway_settings.model,
                    status="FALLBACK",
                    failure_class=failure_class,
                    fallback_used=True,
                )
            )
            safe_increment_metric(METRIC_TIMEOUT_TOTAL)
            safe_increment_metric(METRIC_FAILURES_TOTAL)
            safe_increment_metric(METRIC_FALLBACK_TOTAL)

            return JSONResponse(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                content={
                    "error": "GATEWAY_TIMEOUT",
                    "detail": "AI 伴学服务响应超时，请稍后重试。",
                    "grounding_status": "insufficient_context",
                    "answer": "抱歉，伴学服务响应超时，请稍后重试。",
                },
                headers={"X-Request-ID": request_id},
            )

        except ProviderException as e:
            latency_ms = round((time.perf_counter() - start_perf) * 1000, 2)
            clean_err = sanitize_exception_message(e)
            logger.error(f"Gateway provider error [{request_id}]: {clean_err}")

            fail_enum = classify_provider_exception(e)
            failure_class = fail_enum.value
            if fail_enum == ProviderFailureClass.PROVIDER_POLICY_VIOLATION:
                safe_increment_metric(METRIC_POLICY_VIOLATIONS_TOTAL)

            safe_record_audit(
                AuditEvent(
                    event_name="PROVIDER_FAILED",
                    request_id=request_id,
                    provider=provider.provider_name,
                    model=gateway_settings.model,
                    status="FAILED",
                    failure_class=failure_class,
                    latency_ms=latency_ms,
                )
            )
            safe_record_audit(
                AuditEvent(
                    event_name="FALLBACK_ACTIVATED",
                    request_id=request_id,
                    provider=provider.provider_name,
                    model=gateway_settings.model,
                    status="FALLBACK",
                    failure_class=failure_class,
                    fallback_used=True,
                )
            )
            safe_increment_metric(METRIC_FAILURES_TOTAL)
            safe_increment_metric(METRIC_FALLBACK_TOTAL)

            return JSONResponse(
                status_code=status.HTTP_502_BAD_GATEWAY,
                content={
                    "error": "BAD_GATEWAY",
                    "detail": "AI 服务商暂时不可用，已安全拦截。",
                    "grounding_status": "insufficient_context",
                    "answer": "抱歉，伴学服务商暂时不可用，请稍后重试。",
                },
                headers={"X-Request-ID": request_id},
            )

    # ============================================================
    # Phase 4 / Sprint 8-A: Product Learning Loop MVP 端点
    # ============================================================

    @application.get("/api/concept/{knowledge_id}")
    def get_concept_card_endpoint(knowledge_id: str) -> Dict[str, Any]:
        """获取指定知识点概念微卡片（先学后测，1分钟核心概念速成）"""
        card = get_concept_card(knowledge_id)
        if not card:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"未找到知识点 {knowledge_id} 的考点速览卡片",
            )
        return card.model_dump()

    @application.get("/api/concept")
    def get_all_concepts_endpoint() -> Dict[str, Any]:
        """获取全图谱 30 个考点概念微卡片列表"""
        cards = get_all_concept_cards()
        return {
            "total": len(cards),
            "concept_cards": [c.model_dump() for c in cards],
        }

    @application.get("/api/quiz/{knowledge_id}", response_model=QuizKnowledgeListResponse)
    def get_quiz_questions_endpoint(knowledge_id: str) -> QuizKnowledgeListResponse:
        """按知识点获取微测验题目（30/30 考点全覆盖，脱敏不包含正确答案）"""
        if not knowledge_graph_service.is_valid_knowledge_id(knowledge_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"未找到对应知识点：{knowledge_id}",
            )
        raw_kp = knowledge_graph_service.get_knowledge_point(knowledge_id) or {}
        knowledge_name = raw_kp.get("knowledge_name", knowledge_id)

        matched = get_public_questions_by_knowledge_id(knowledge_id)
        if not matched:
            from app.services import quiz_service as app_quiz_service
            try:
                return app_quiz_service.get_questions_by_knowledge_id(knowledge_id)
            except Exception:
                pass

        return QuizKnowledgeListResponse(
            knowledge_id=knowledge_id,
            knowledge_name=knowledge_name,
            questions=[
                QuizQuestionPublic(
                    question_id=q.question_id,
                    knowledge_id=q.knowledge_id,
                    stem=q.stem,
                    options=[QuizOption(key=opt.key, text=opt.text) for opt in q.options],
                    difficulty=q.difficulty,
                )
                for q in matched
            ],
        )

    @application.post("/api/quiz/submit", response_model=QuizSubmitResponse)
    def submit_quiz_answer_endpoint(req: QuizSubmitRequest) -> QuizSubmitResponse:
        """
        提交微测验作答，全流程闭环：
        1. 优先查 35 题全集题库
        2. 校验选项合法性
        3. 服务端判题
        4. 记录 QUESTION_ATTEMPT 学习事件
        5. 驱动 BKT 状态演进
        6. 驱动 PathState 局部动态重规划
        7. 返回判题结果与学情快照
        """
        question = get_content_question_by_id(req.question_id)
        if not question:
            from app.services.quiz_service import get_question_by_id as get_app_q
            question = get_app_q(req.question_id)

        if not question:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"题目不存在：{req.question_id}",
            )

        valid_option_keys = [opt.key for opt in question.options]
        if req.selected_option not in valid_option_keys:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f"非法选项：{req.selected_option}，可选选项为：{valid_option_keys}",
            )

        is_correct = (req.selected_option == question.answer)

        event_id = f"evt-quiz-{uuid.uuid4().hex[:12]}"
        client_ts = datetime.now(timezone.utc).astimezone().isoformat()
        event_payload = {
            "question_id": question.question_id,
            "is_correct": is_correct,
            "selected_option": req.selected_option,
        }
        if req.time_spent_ms is not None:
            event_payload["time_spent_ms"] = req.time_spent_ms

        event_in = LearningEventCreate(
            event_id=event_id,
            student_id=req.student_id,
            knowledge_id=question.knowledge_id,
            event_type="QUESTION_ATTEMPT",
            payload=event_payload,
            client_timestamp=client_ts,
        )
        stored_event = default_event_repository.record_event(event_in)

        learning_state = None
        replanning_envelope = None
        try:
            bkt_res = bkt_event_processor.process_event(stored_event)
            if bkt_res.status == "updated" and bkt_res.state is not None:
                prob = bkt_res.state.mastery_probability
                learning_state = LearningStateSnapshot(
                    updated=True,
                    mastery_probability=prob,
                    mastery_percent=round(prob * 100.0, 2),
                    state=get_mastery_state(prob),
                    attempts=bkt_res.state.attempts,
                    consecutive_correct=bkt_res.state.consecutive_correct,
                )
                try:
                    prev_mastered = (bkt_res.before_mastery is not None and bkt_res.before_mastery >= 0.80)
                    replanning_envelope = evaluate_and_replan(
                        student_id=req.student_id,
                        knowledge_id=question.knowledge_id,
                        before_mastery=bkt_res.before_mastery or 0.20,
                        after_mastery=bkt_res.after_mastery or bkt_res.state.mastery_probability,
                        consecutive_incorrect=bkt_res.state.consecutive_incorrect,
                        previously_mastered=prev_mastered,
                        is_task_context=True,
                        trace_id=stored_event.event_id,
                    )
                except Exception as e:
                    logger.warning(f"Replanning error: {e}")
                    replanning_envelope = None
            elif bkt_res.status == "already_processed" and bkt_res.state is not None:
                prob = bkt_res.state.mastery_probability
                learning_state = LearningStateSnapshot(
                    updated=False,
                    mastery_probability=prob,
                    mastery_percent=round(prob * 100.0, 2),
                    state=get_mastery_state(prob),
                    attempts=bkt_res.state.attempts,
                    consecutive_correct=bkt_res.state.consecutive_correct,
                    reason="事件已处理（幂等去重）",
                )
        except Exception as exc:
            logger.error(f"BKT event processor error: {exc}")
            learning_state = None

        return QuizSubmitResponse(
            is_correct=is_correct,
            correct_option=question.answer,
            explanation=question.explanation,
            knowledge_id=question.knowledge_id,
            question_id=question.question_id,
            event_id=event_id,
            learning_state=learning_state,
            replanning=replanning_envelope,
        )

    @application.post("/api/students/init", response_model=StudentInitResponse)
    def init_student_endpoint(req: StudentInitRequest) -> StudentInitResponse:
        """轻量级 Demo 学生初始化：设定目标并就绪 30 节点学习路径"""
        sid = req.student_id or f"DEMO_{int(time.time()) % 9000 + 1000}"
        initial_states = {
            f"K{i:02d}": PathState.LOCKED for i in range(1, 31)
        }
        start_kp = req.start_knowledge_id if req.start_knowledge_id in initial_states else "K01"
        initial_states[start_kp] = PathState.IN_PROGRESS
        path_state_service.init_student_path(sid, initial_states)

        profile = {
            "student": {
                "student_id": sid,
                "student_name": req.student_name,
                "major": req.major,
                "grade": req.grade,
                "learning_goal": req.learning_goal,
                "class_name": req.class_name or "微观经济学",
            },
            "overall_profile": {
                "average_accuracy": 0.0,
                "answer_time_seconds": 0.0,
                "practice_count": 0,
                "mastery_level": "薄弱",
                "study_mode": "adaptive",
            },
            "weak_knowledge_points": [start_kp],
            "strong_knowledge_points": [],
        }
        DEMO_STUDENTS[sid] = profile

        return StudentInitResponse(
            student_id=sid,
            student_name=req.student_name,
            major=req.major,
            grade=req.grade,
            learning_goal=req.learning_goal,
            class_name=req.class_name or "微观经济学",
            current_knowledge_id=start_kp,
            path_states={k: v.value for k, v in initial_states.items()},
            message=f"学生 {req.student_name} 初始化成功，学习路径已重置并就绪",
        )

    @application.get("/api/students")
    def get_all_students_endpoint() -> Dict[str, Any]:
        """获取所有学生列表（预设种子学生 S001~S005 + 动态初始化的 Demo 学生）"""
        from app.services.student_service import student_service
        students_data = student_service.get_all_students()
        items = list(students_data)
        for sid, p in DEMO_STUDENTS.items():
            st = p["student"]
            ov = p["overall_profile"]
            items.append({
                "student_id": sid,
                "student_name": st["student_name"],
                "major": st["major"],
                "grade": st["grade"],
                "learning_goal": st["learning_goal"],
                "class_name": st.get("class_name", ""),
                "average_accuracy": ov["average_accuracy"],
                "answer_time_seconds": ov["answer_time_seconds"],
                "practice_count": ov["practice_count"],
                "mastery_level": ov["mastery_level"],
            })
        return {"count": len(items), "students": items}

    @application.get("/api/students/{student_id}/dashboard")
    def get_student_dashboard_endpoint(student_id: str) -> Dict[str, Any]:
        """获取学生看板（预设学生委托给业务层，Demo 学生动态合成）"""
        from app.services.student_service import student_service
        dashboard = student_service.get_student_dashboard(student_id)
        if dashboard:
            return dashboard

        if student_id in DEMO_STUDENTS:
            p = DEMO_STUDENTS[student_id]
            st = p["student"]
            path_states = path_state_service.get_all_path_states(student_id)
            curr = "K01"
            for kid, state in path_states.items():
                if state == PathState.IN_PROGRESS:
                    curr = kid
                    break
            return {
                "student_id": student_id,
                "profile": p,
                "learning_path": {
                    "student_id": student_id,
                    "target_goal": st["learning_goal"],
                    "current_focus_node": curr,
                    "recommended_sequence": list(path_states.keys()),
                    "path_states": {k: v.value for k, v in path_states.items()},
                },
                "report": {
                    "student_id": student_id,
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                    "overall_score": 75.0,
                    "weak_points": [curr],
                    "recommendations": ["建议优先攻坚当前聚焦考点"],
                },
            }
        raise HTTPException(status_code=404, detail=f"找不到学生：{student_id}")

    @application.get("/api/students/{student_id}/path-states")
    def get_student_path_states_endpoint(student_id: str) -> Dict[str, Any]:
        """获取指定学生的 30 考点路径执行状态（支持预设与 Demo 学生）"""
        from app.services.student_service import student_service
        profile = student_service.get_student_profile(student_id)
        if not profile and student_id not in DEMO_STUDENTS:
            raise HTTPException(status_code=404, detail=f"找不到学生：{student_id}")
        states = path_state_service.get_all_path_states(student_id)
        return {
            "student_id": student_id,
            "states": {k: v.value for k, v in states.items()},
        }

    # 挂载核心业务应用为子路由兜底
    application.mount("/", app_main)

    return application


app = create_gateway_app()
