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
from typing import Any, Dict, List, Optional, Union
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
from gateway.learning.diagnostic import (
    DiagnosticResult,
    PretestSession,
    PretestSubmitRequest,
    create_pretest_session,
    evaluate_pretest,
    get_pretest_session,
)
from gateway.learning.path_generation import (
    DynamicLearningRoute,
    default_dynamic_path_generator,
)
from gateway.learning.graph import (
    apply_route_overlay_to_graph,
    get_route_graph_overlay,
)
from gateway.learning.analytics import (
    ProgressHistoryEvent,
    StudentProgressResponse,
    WrongAnswerReviewResponse,
    TeacherOverviewResponse,
    TeacherStudentDetailResponse,
    TeacherStudentSummary,
    default_analytics_service,
)
from gateway.learning.companion import (
    CompanionStudyRequest,
    CompanionStudyResponse,
    CompanionSession,
    CompanionSuggestedAction,
    QuickCheckOption,
    QuickCheckQuestion,
    QuickCheckSubmitRequest,
    QuickCheckResponse,
    LearningActionResultRequest,
    LearningActionResultResponse,
    record_companion_event,
    default_companion_service,
)
from gateway.learning.resources import (
    ResourceType,
    LearningResource,
    ResourceRecommendation,
    RecommendedResourcesResponse,
    ResourceListResponse,
    ResourceEventPayload,
    VALID_RESOURCE_EVENT_TYPES,
    get_resource_by_id,
    get_resources_by_knowledge,
    get_unified_resource_by_id,
    get_unified_resources_by_knowledge,
    default_resource_resolver,
    record_resource_event,
)
from gateway.learning.effectiveness import (
    LearningSession,
    LearningSessionCreateRequest,
    LearningSessionCompleteRequest,
    SessionCompleteResponse,
    LearningEffectiveness,
    KnowledgeEffectivenessResponse,
    default_session_service,
    default_effectiveness_analyzer,
)
from gateway.learning.resource_effectiveness import (
    EffectivenessProfileResponse,
    ResourceEffectivenessProfile,
    default_resource_effectiveness_aggregator,
)
from gateway.learning.resource_effectiveness.aggregator import normalize_resource_type_key
from gateway.learning.retention import (
    RetentionProfile,
    RetentionStatus,
    default_retention_analyzer,
)
from gateway.learning.today import (
    TodayActionResponse,
    default_today_action_resolver,
)
from gateway.content.concept_cards import CONCEPT_CARDS
from gateway.teacher_actions import (
    TeacherActionCreateRequest,
    TeacherActionItem,
    TeacherActionHistoryResponse,
    StudentRecommendationsResponse,
    TeacherActionRepository,
    default_teacher_action_repository,
)
from gateway.ai.deepseek import (
    AuthenticationError,
    PIIViolationError,
    ProviderDisabledError,
    ProviderTimeout,
    ProviderUnavailableError,
    RateLimitError,
)
from gateway.ai.recommendation import (
    RecommendationRequest,
    RecommendationResponse,
    ValidationRejectedError,
    default_recommendation_service,
)

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


class PretestCreateRequest(BaseModel):
    student_id: str = Field(..., description="学生ID")
    goal: Optional[str] = Field(default="微观经济学核心概念掌握与考点突破", description="学习目标")


class PretestSubmitResponse(BaseModel):
    diagnostic: DiagnosticResult = Field(..., description="综合学情诊断报告")
    dynamic_route: DynamicLearningRoute = Field(..., description="诊断后即时生成的动态学习路线")


class CompanionResetRequest(BaseModel):
    student_id: str = Field(..., description="学生唯一标识")


class TeacherKnowledgeItem(BaseModel):
    knowledge_id: str
    knowledge_name: str
    chapter: str
    average_mastery: float
    student_count: int
    weak_student_count: int
    total_mistakes: int
    urgency: str = "MEDIUM"


class TeacherKnowledgeResponse(BaseModel):
    total_count: int
    knowledge_points: List[TeacherKnowledgeItem]


class TeacherDiagnosisStudentItem(BaseModel):
    """教师诊断中指定考点的单生学情客观数据 (Sprint 10-D Phase 3)"""
    student_id: str
    student_name: str
    major: str
    grade: str
    mastery: float
    risk_level: str
    attempts: int = 0
    mistake_count: int = 0


class TeacherKnowledgeDiagnosisResponse(BaseModel):
    """教师诊断指定考点的班级学情与学生下钻聚合模型 (Sprint 10-D Phase 3)"""
    knowledge_id: str
    knowledge_name: str
    chapter: str
    average_mastery: float
    student_count: int
    weak_student_count: int
    total_mistakes: int
    urgency: str = "MEDIUM"
    students: List[TeacherDiagnosisStudentItem]


# 动态初始化的 Demo 学生档案注册表（内存态，支持测试与体验会话）
DEMO_STUDENTS: Dict[str, Dict[str, Any]] = {}


def create_gateway_app(
    teacher_action_repo: Optional[TeacherActionRepository] = None,
) -> FastAPI:
    """构建独立 AI Gateway FastAPI 应用实例"""
    active_teacher_action_repo = teacher_action_repo or default_teacher_action_repository

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
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
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

    @application.get("/health")
    @application.get("/api/health")
    @application.get("/api/ai/health")
    def health_check() -> Dict[str, Any]:
        """网关健康检查探针 (静态就绪状态，不发起外部探活网络请求)"""
        deepseek_configured = bool(gateway_settings.deepseek_api_key and gateway_settings.deepseek_api_key.strip())
        return {
            "status": "healthy",
            "provider": gateway_settings.provider,
            "masked_key": gateway_settings.get_masked_api_key(),
            "timeout_ms": gateway_settings.timeout_ms,
            "deepseek": {
                "enabled": gateway_settings.deepseek_enabled,
                "configured": deepseek_configured,
                "model": gateway_settings.deepseek_model,
                "base_url": gateway_settings.deepseek_base_url,
                "reachable": "unknown",  # 默认不产生外部网络请求
            },
        }

    @application.post(
        "/api/ai/recommendations/{student_id}",
        response_model=RecommendationResponse,
        response_model_exclude_unset=True,
    )
    async def recommendation_endpoint(
        student_id: str,
        response: Response,
        request: Optional[RecommendationRequest] = None,
    ) -> RecommendationResponse:
        """
        AI 个性化学习资源推荐候选端点 (只读、安全、确定性、零学习副作用)
        
        红线约束：
        1. 绝不产生 QUESTION_ATTEMPT, RESOURCE_VIEW, BKT_UPDATE, PATH_UPDATE 等业务学习事件；
        2. 严格通过三层确定性校验，拒绝任何越权或上下文外 ID；
        3. 客户端不可指定 model，模型配置由服务端统一收敛。
        """
        request_id = generate_request_id()
        response.headers["X-Request-ID"] = request_id

        req = request or RecommendationRequest(student_id=student_id)
        if not req.student_id:
            req = req.model_copy(update={"student_id": student_id})

        try:
            return await default_recommendation_service.get_recommendations(
                student_id=student_id,
                request=req,
            )
        except ValidationRejectedError as vre:
            logger.warning(f"Recommendation validation rejected [{request_id}]: {vre.message}")
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"AI 推荐候选未通过确定性安全校验: {vre.message}",
            )
        except PIIViolationError as pve:
            logger.error(f"Recommendation PII violation [{request_id}]: {pve.message}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="请求或上下文包含敏感个人信息，已被安全网关拦截",
            )
        except ProviderDisabledError as pde:
            logger.warning(f"Recommendation provider disabled [{request_id}]: {pde.message}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="AI 推荐服务当前已禁用 (DEEPSEEK_ENABLED=false)",
            )
        except ProviderTimeout as pte:
            logger.error(f"Recommendation provider timeout [{request_id}]: {pte.message}")
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail="AI 推荐服务响应超时，请稍后重试",
            )
        except RateLimitError as rle:
            logger.warning(f"Recommendation rate limited [{request_id}]: {rle.message}")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="AI 推荐服务请求过于频繁，请稍后重试",
            )
        except AuthenticationError as ae:
            logger.error(f"Recommendation authentication error [{request_id}]: {ae.message}")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="AI 推荐上游服务凭证异常",
            )
        except ProviderUnavailableError as pue:
            logger.error(f"Recommendation provider unavailable [{request_id}]: {pue.message}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="AI 推荐上游服务暂不可用",
            )
        except ProviderException as pe:
            logger.error(f"Recommendation provider error [{request_id}]: {pe}")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"AI 推荐服务异常: {pe}",
            )
        except Exception as e:
            logger.error(f"Recommendation unexpected error [{request_id}]: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="推荐服务生成发生未知异常，请稍后重试",
            )

    @application.post(
        "/api/ai/companion",
        response_model=Union[CompanionStudyResponse, StructuredAIResponse],
        response_model_exclude_unset=True,
    )
    async def companion_endpoint(
        request: Union[CompanionStudyRequest, AICompanionRequest],
        response: Response,
    ) -> Union[CompanionStudyResponse, StructuredAIResponse]:
        """
        AI 伴学主入口端点
        
        加固执行边界：
        1. Request Correlation: 注入 X-Request-ID Header 保证链路追踪
        2. Latency & Observability: 旁路收集耗时与状态事件，Fail-safe 熔断保护
        3. Request Validation: Pydantic 严格白名单校验 (extra='forbid')
        4. Provider Selection & Invocation: 委托给 AIProviderAdapter 抽象层
        5. Response Normalization: 仅返回契约字段
        6. Secret & Authority Isolation: 密钥绝不暴露，决策权绝对隔离
        """
        request_id = generate_request_id()
        response.headers["X-Request-ID"] = request_id
        start_perf = time.perf_counter()

        # Phase 5 / Sprint 9-A: AI 学习伙伴双层架构分发
        if isinstance(request, CompanionStudyRequest):
            try:
                study_res = await default_companion_service.handle_companion_request(request)
                return study_res
            except ValueError as ve:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=str(ve),
                )
            except Exception as e:
                logger.error(f"Companion service error [{request_id}]: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="伴学服务内部异常，请稍后重试",
                )

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
    # Sprint 9-A: AI 伴学会话管理端点
    # ============================================================

    @application.post("/api/ai/companion/reset")
    def reset_companion_session_endpoint(req: CompanionResetRequest) -> Dict[str, Any]:
        """重置指定学生的伴学对话上下文 (Sprint 9-A)"""
        default_companion_service.reset_student_session(req.student_id)
        return {"status": "reset", "student_id": req.student_id}

    @application.get("/api/ai/companion/sessions/{session_id}", response_model=CompanionSession)
    def get_companion_session_endpoint(session_id: str) -> CompanionSession:
        """获取指定伴学会话记录 (Sprint 9-A)"""
        sess = default_companion_service.get_session(session_id)
        if not sess:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"未找到伴学会话：{session_id}",
            )
        return sess

    # ============================================================
    # Sprint 9-B: AI Guided Learning & Learning Reflection 端点
    # ============================================================

    @application.get("/api/ai/companion/quick-check/{knowledge_id}", response_model=QuickCheckQuestion)
    def get_quick_check_endpoint(knowledge_id: str) -> QuickCheckQuestion:
        """获取指定考点的轻量快速思维检查题目（零BKT副作用，非正式测验）(Sprint 9-B)"""
        q = default_companion_service.get_quick_check(knowledge_id)
        if not q:
            raise HTTPException(status_code=404, detail=f"未找到考点快速思维检查：{knowledge_id}")
        return q

    @application.post("/api/ai/companion/quick-check", response_model=QuickCheckResponse)
    def submit_quick_check_endpoint(req: QuickCheckSubmitRequest) -> QuickCheckResponse:
        """提交快速思维检查作答，即时获取启发式解析与正式测验验证指引 (Sprint 9-B)"""
        return default_companion_service.evaluate_quick_check(
            student_id=req.student_id,
            check_id=req.check_id,
            knowledge_id=req.knowledge_id,
            selected_option=req.selected_option,
        )

    @application.post("/api/ai/companion/action-result", response_model=LearningActionResultResponse)
    def post_learning_action_result_endpoint(req: LearningActionResultRequest) -> LearningActionResultResponse:
        """完成学习行动后向伴学导师上报，AI重新读取真实掌握度并给出复盘与下一步Guided Actions (Sprint 9-B)"""
        return default_companion_service.reflect_action_result(req)

    @application.get("/api/ai/companion/actions/{student_id}")
    def get_student_companion_actions_endpoint(
        student_id: str, knowledge_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """获取指定学生当前考点的确定性 Guided Actions 列表 (Sprint 9-B)"""
        from app.services.student_service import student_service
        profile = student_service.get_student_profile(student_id)
        if not profile and student_id not in DEMO_STUDENTS:
            raise HTTPException(status_code=404, detail=f"找不到学生：{student_id}")
        actions = default_companion_service.get_student_guided_actions(student_id, knowledge_id)
        return {
            "student_id": student_id,
            "knowledge_id": knowledge_id,
            "actions": [a.model_dump() for a in actions],
        }

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
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
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

        if (
            req.student_id in DEMO_STUDENTS
            and isinstance(DEMO_STUDENTS[req.student_id], dict)
            and "overall_profile" in DEMO_STUDENTS[req.student_id]
        ):
            dp = DEMO_STUDENTS[req.student_id]["overall_profile"]
            dp["practice_count"] = dp.get("practice_count", 0) + 1
            curr_correct = dp.get("_correct_count", 0) + (1 if is_correct else 0)
            dp["_correct_count"] = curr_correct
            dp["average_accuracy"] = round((curr_correct / dp["practice_count"]) * 100.0, 1)

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

            route = default_dynamic_path_generator.generate_route(
                student_id=student_id,
                goal=st.get("learning_goal", "微观经济学核心概念掌握与考点突破"),
            )
            learning_path_steps = [
                {
                    "stage": s.rank,
                    "knowledge_id": s.knowledge_id,
                    "knowledge_name": s.knowledge_name,
                    "chapter": s.chapter,
                    "current_accuracy": 0.0 if p.get("overall_profile", {}).get("practice_count", 0) == 0 else round(s.mastery * 100, 1),
                    "priority": "高" if s.role == "CURRENT" else "中",
                    "priority_score": round(s.score * 100, 1),
                    "source": "动态自适应推荐",
                    "learning_goal": f"掌握{s.knowledge_name}",
                    "reason": s.explanation,
                }
                for s in route.steps
            ]

            return {
                "student_id": student_id,
                "profile": p,
                "learning_path": {
                    "student": st,
                    "profile_summary": {
                        "total_knowledge_points": 30,
                        "mastered_count": 0,
                        "weak_count": len(route.steps),
                        "overall_accuracy": 0.0,
                    },
                    "recommendation_type": "dynamic_adaptive",
                    "learning_path": learning_path_steps,
                    "optimization_suggestion": ["完成前置考点突破以解锁后续进阶内容"],
                    "student_id": student_id,
                    "target_goal": st["learning_goal"],
                    "current_focus_node": curr,
                    "recommended_sequence": [s.knowledge_id for s in route.steps],
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

    @application.get("/api/students/{student_id}/knowledge-graph")
    def get_student_knowledge_graph_endpoint(student_id: str) -> Dict[str, Any]:
        """获取指定学生的微观经济学知识图谱拓扑与学情联动数据（支持预设与 Demo 学生）"""
        base_graph = knowledge_graph_service.get_student_knowledge_graph(student_id)
        if not base_graph and student_id in DEMO_STUDENTS:
            base_graph = knowledge_graph_service.get_student_knowledge_graph("S001")
            if base_graph:
                base_graph["student"] = {"student_id": student_id}
        if not base_graph:
            raise HTTPException(status_code=404, detail=f"找不到学生知识图谱：{student_id}")
        return base_graph

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

    # ============================================================
    # Sprint 8-B: 极速前测、学情诊断与自适应动态路径端点
    # ============================================================

    @application.post("/api/diagnostic/pretest", response_model=PretestSession)
    def create_pretest_endpoint(req: PretestCreateRequest) -> PretestSession:
        """创建 3 题极速前测会话（脱敏，剔除答案与解析）"""
        return create_pretest_session(
            student_id=req.student_id,
            goal=req.goal or "微观经济学核心概念掌握与考点突破",
        )

    @application.post("/api/diagnostic/pretest/{session_id}/submit", response_model=PretestSubmitResponse)
    def submit_pretest_endpoint(session_id: str, req: PretestSubmitRequest) -> PretestSubmitResponse:
        """提交前测作答，评估学情并即时生成首条自适应动态攻坚路线"""
        session = get_pretest_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail=f"前测会话不存在或已过期：{session_id}")
        diagnostic_res = evaluate_pretest(session_id, req.answers)
        dynamic_route = default_dynamic_path_generator.generate_route(
            student_id=diagnostic_res.student_id,
            goal=diagnostic_res.goal,
        )
        return PretestSubmitResponse(
            diagnostic=diagnostic_res,
            dynamic_route=dynamic_route,
        )

    @application.get("/api/path/dynamic/{student_id}", response_model=DynamicLearningRoute)
    def get_dynamic_path_endpoint(student_id: str, goal: Optional[str] = None) -> DynamicLearningRoute:
        """获取指定学生的 Top-3 动态自适应学习路线"""
        actual_goal = goal
        if not actual_goal:
            from app.services.student_service import student_service
            p = student_service.get_student_profile(student_id)
            if p and p.get("student", {}).get("learning_goal"):
                actual_goal = p["student"]["learning_goal"]
            elif student_id in DEMO_STUDENTS:
                actual_goal = DEMO_STUDENTS[student_id]["student"]["learning_goal"]
            else:
                actual_goal = "微观经济学核心概念掌握与考点突破"

        return default_dynamic_path_generator.generate_route(
            student_id=student_id,
            goal=actual_goal,
        )

    @application.get("/api/path/dynamic/{student_id}/explanation")
    def get_dynamic_path_explanation_endpoint(student_id: str, goal: Optional[str] = None) -> Dict[str, Any]:
        """获取动态路径的结构化推荐理由与证据说明"""
        route = get_dynamic_path_endpoint(student_id, goal)
        overlay = get_route_graph_overlay(student_id, route)
        return {
            "student_id": student_id,
            "goal": route.goal,
            "route_length": route.route_length,
            "is_fallback": route.is_fallback,
            "fallback_reason": route.fallback_reason,
            "steps": [s.model_dump() for s in route.steps],
            "overlay": overlay,
        }

    @application.get("/api/students/{student_id}/knowledge-graph/dynamic")
    def get_student_dynamic_knowledge_graph_endpoint(student_id: str, goal: Optional[str] = None) -> Dict[str, Any]:
        """获取叠加了动态航线高亮与流动动画的知识图谱数据"""
        base_graph = knowledge_graph_service.get_student_knowledge_graph(student_id)
        if not base_graph and student_id in DEMO_STUDENTS:
            base_graph = knowledge_graph_service.get_student_knowledge_graph("S001")
            if base_graph:
                base_graph["student"] = {"student_id": student_id}
        if not base_graph:
            raise HTTPException(status_code=404, detail=f"无法获取学生知识图谱：{student_id}")
        route = get_dynamic_path_endpoint(student_id, goal)
        return apply_route_overlay_to_graph(base_graph, route)

    # -------------------------------------------------------------------------
    # Sprint 8-C: 学习成效沉淀、掌握度历史、错题复盘与教师学习分析 API
    # -------------------------------------------------------------------------
    default_analytics_service.set_demo_students(DEMO_STUDENTS)

    @application.get("/api/students/{student_id}/progress", response_model=StudentProgressResponse)
    def get_student_progress_endpoint(student_id: str) -> StudentProgressResponse:
        """获取指定学生的客观学习成效历史、答题趋势与 30 考点掌握全景 (Sprint 8-C)"""
        prog = default_analytics_service.get_student_progress(student_id)
        if not prog:
            raise HTTPException(status_code=404, detail=f"找不到学生学情进展：{student_id}")
        return prog

    @application.get("/api/students/{student_id}/wrong-answers", response_model=WrongAnswerReviewResponse)
    def get_student_wrong_answers_endpoint(student_id: str) -> WrongAnswerReviewResponse:
        """获取指定学生的全部真实错题复盘列表（按掌握度与错误频次自适应排序）(Sprint 8-C)"""
        res = default_analytics_service.get_student_wrong_answers(student_id)
        if res is None:
            raise HTTPException(status_code=404, detail=f"找不到学生错题记录：{student_id}")
        return res

    class EventPayloadInput(BaseModel):
        event_id: Optional[str] = None
        student_id: str = Field(..., min_length=1)
        knowledge_id: str = Field(default="K01", min_length=1)
        event_type: str = Field(..., min_length=1)
        payload: Dict[str, Any] = Field(default_factory=dict)
        client_timestamp: Optional[str] = None

    @application.post("/api/learning/events")
    def record_learning_event_endpoint(event_in: EventPayloadInput) -> Dict[str, Any]:
        """轻量记录学习行为与辅学行为日志（如 CONCEPT_VIEW、AI_ACTION_CLICK 等）(Sprint 8-C / 9-B)"""
        if event_in.event_type in {"AI_ACTION_VIEW", "AI_ACTION_CLICK", "AI_GUIDED_SESSION", "AI_QUICK_CHECK"}:
            stored = record_companion_event(
                event_type=event_in.event_type,
                student_id=event_in.student_id,
                knowledge_id=event_in.knowledge_id,
                payload=event_in.payload,
                client_timestamp=event_in.client_timestamp,
            )
            return {
                "status": "recorded",
                "event_id": stored["event_id"],
                "server_timestamp": stored["server_timestamp"],
            }
        elif event_in.event_type in VALID_RESOURCE_EVENT_TYPES:
            dur = event_in.payload.get("duration_seconds")
            stored = record_resource_event(
                student_id=event_in.student_id,
                resource_id=event_in.payload.get("resource_id", f"res_{event_in.knowledge_id.lower()}"),
                knowledge_id=event_in.knowledge_id,
                event_type=event_in.event_type,
                duration_seconds=dur,
                metadata=event_in.payload,
                client_timestamp=event_in.client_timestamp,
            )
            return {
                "status": "recorded",
                "event_id": stored["event_id"],
                "server_timestamp": stored["server_timestamp"],
            }
        else:
            evt_create = LearningEventCreate(
                event_id=event_in.event_id or f"evt-{uuid.uuid4().hex[:12]}",
                student_id=event_in.student_id,
                knowledge_id=event_in.knowledge_id,
                event_type=event_in.event_type,
                payload=event_in.payload,
                client_timestamp=event_in.client_timestamp or datetime.now(timezone.utc).isoformat(),
            )
            stored_domain = default_event_repository.record_event(evt_create)
            return {
                "status": "recorded",
                "event_id": stored_domain.event_id,
                "server_timestamp": stored_domain.server_timestamp,
            }

    # -------------------------------------------------------------------------
    # 学习资源中心端点 (Sprint 9-C: Learning Resource Hub Endpoints)
    # -------------------------------------------------------------------------
    @application.post("/api/learning/resources/events")
    def record_resource_event_endpoint(payload: ResourceEventPayload) -> Dict[str, Any]:
        """记录学习资源辅助交互日志（物理隔离写入 data/resource_events.jsonl）(Sprint 9-C)"""
        stored = record_resource_event(
            student_id=payload.student_id,
            resource_id=payload.resource_id,
            knowledge_id=payload.knowledge_id,
            event_type=payload.event_type,
            duration_seconds=payload.duration_seconds,
            metadata=payload.metadata,
            client_timestamp=payload.client_timestamp,
        )
        return {
            "status": "recorded",
            "event_id": stored["event_id"],
            "server_timestamp": stored["server_timestamp"],
        }

    @application.get("/api/learning/resources/recommended/{student_id}", response_model=RecommendedResourcesResponse)
    def get_recommended_resources_endpoint(
        student_id: str,
        knowledge_id: Optional[str] = None,
    ) -> RecommendedResourcesResponse:
        """根据学生当前掌握度与做题状态，确定性输出自适应资源推荐清单 (Sprint 9-C)"""
        student_info = default_companion_service.context_builder.resolve_student(student_id)
        if not student_info:
            raise HTTPException(status_code=404, detail=f"找不到学生档案：{student_id}")

        if knowledge_id and knowledge_id not in CONCEPT_CARDS:
            raise HTTPException(status_code=404, detail=f"找不到指定考点：{knowledge_id}")

        return default_resource_resolver.resolve(student_id=student_id, knowledge_id=knowledge_id)

    @application.get("/api/learning/resources/item/{resource_id}", response_model=LearningResource)
    def get_resource_item_endpoint(resource_id: str) -> LearningResource:
        """获取单个学习资源详情（支持内部资源与中国大学MOOC外部资源）"""
        item = get_unified_resource_by_id(resource_id)
        if not item:
            raise HTTPException(status_code=404, detail=f"找不到学习资源：{resource_id}")
        return item

    @application.get(
        "/api/learning/resources/effectiveness-profile/{student_id}",
        response_model=EffectivenessProfileResponse,
    )
    def get_resource_effectiveness_profile_endpoint(
        student_id: str,
        knowledge_id: Optional[str] = None,
    ) -> EffectivenessProfileResponse:
        """获取学生针对特定考点的资源历史学习效果档案 (Sprint 9-E)"""
        student_info = default_companion_service.context_builder.resolve_student(student_id)
        if not student_info:
            raise HTTPException(status_code=404, detail=f"找不到学生档案：{student_id}")

        target_kid = knowledge_id or "K01"
        if target_kid not in CONCEPT_CARDS:
            raise HTTPException(status_code=404, detail=f"找不到指定考点：{target_kid}")

        profile_map = default_resource_effectiveness_aggregator.get_resource_effectiveness(
            student_id=student_id,
            knowledge_id=target_kid,
        )

        unique_profiles: Dict[str, ResourceEffectivenessProfile] = {}
        for k, prof in profile_map.items():
            norm_k = normalize_resource_type_key(prof.resource_type)
            if norm_k not in unique_profiles:
                unique_profiles[norm_k] = prof

        return EffectivenessProfileResponse(
            student_id=student_id,
            knowledge_id=target_kid,
            profiles=list(unique_profiles.values()),
        )

    @application.get("/api/learning/resources/{knowledge_id}", response_model=ResourceListResponse)
    def get_knowledge_resources_endpoint(
        knowledge_id: str,
        resource_type: Optional[str] = None,
        source: Optional[str] = None,
    ) -> ResourceListResponse:
        """获取指定考点的全量学习材料列表（统一支持内部资源与中国大学MOOC外部资源）"""
        if knowledge_id not in CONCEPT_CARDS:
            raise HTTPException(status_code=404, detail=f"找不到指定考点：{knowledge_id}")

        r_type = None
        if resource_type:
            try:
                r_type = ResourceType(resource_type)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"不支持的资源类型: {resource_type}")

        norm_source = (source or "all").strip().lower()
        if norm_source not in ("all", "xuehai_internal", "internal", "china_mooc", "mooc"):
            raise HTTPException(status_code=400, detail=f"不支持的资源来源: {source}")

        resources = get_unified_resources_by_knowledge(
            knowledge_id=knowledge_id,
            resource_type=r_type,
            source=norm_source,
        )
        return ResourceListResponse(
            knowledge_id=knowledge_id,
            total=len(resources),
            resources=resources,
        )

    # -------------------------------------------------------------------------
    # Sprint 9-D: 学习会话生命周期与学习效果评估及反馈 API
    # -------------------------------------------------------------------------
    @application.post("/api/learning/sessions", response_model=LearningSession)
    def create_learning_session_endpoint(payload: LearningSessionCreateRequest) -> LearningSession:
        """创建新的学习会话，服务端权威快照 initial_mastery (Sprint 9-D)"""
        student_info = default_companion_service.context_builder.resolve_student(payload.student_id)
        if not student_info:
            raise HTTPException(status_code=404, detail=f"找不到学生档案：{payload.student_id}")

        if payload.knowledge_id not in CONCEPT_CARDS:
            raise HTTPException(status_code=404, detail=f"找不到指定考点：{payload.knowledge_id}")

        try:
            return default_session_service.create_session(
                student_id=payload.student_id,
                knowledge_id=payload.knowledge_id,
                resource_ids=payload.resource_ids,
            )
        except KeyError as e:
            raise HTTPException(status_code=404, detail=str(e))

    @application.get("/api/learning/sessions/{session_id}", response_model=LearningSession)
    def get_learning_session_endpoint(session_id: str, student_id: Optional[str] = None) -> LearningSession:
        """查询指定学习会话，强校验学生上下文隔离 (Sprint 9-D)"""
        try:
            return default_session_service.get_session(session_id, request_student_id=student_id)
        except KeyError:
            raise HTTPException(status_code=404, detail=f"找不到指定的学习会话：{session_id}")
        except PermissionError as pe:
            raise HTTPException(status_code=403, detail=str(pe))

    @application.post("/api/learning/sessions/{session_id}/complete", response_model=SessionCompleteResponse)
    def complete_learning_session_endpoint(session_id: str, payload: LearningSessionCompleteRequest) -> SessionCompleteResponse:
        """完成学习会话，服务端权威读取 final_mastery 并计算 delta 与效果评价 (Sprint 9-D)"""
        try:
            completed_session = default_session_service.complete_session(
                session_id=session_id,
                student_id=payload.student_id,
                completed_resource_ids=payload.completed_resource_ids,
                quiz_question_id=payload.quiz_question_id,
                quiz_result=payload.quiz_result,
            )
            effectiveness = default_effectiveness_analyzer.analyze_session(completed_session)
            return SessionCompleteResponse(
                session=completed_session,
                effectiveness=effectiveness,
            )
        except KeyError:
            raise HTTPException(status_code=404, detail=f"找不到指定的学习会话：{session_id}")
        except PermissionError as pe:
            raise HTTPException(status_code=403, detail=str(pe))

    @application.get("/api/learning/resources/{knowledge_id}/effectiveness", response_model=KnowledgeEffectivenessResponse)
    def get_knowledge_effectiveness_endpoint(knowledge_id: str, student_id: str) -> KnowledgeEffectivenessResponse:
        """获取指定考点的学习效果与历史表现信号 (Sprint 9-D)"""
        student_info = default_companion_service.context_builder.resolve_student(student_id)
        if not student_info:
            raise HTTPException(status_code=404, detail=f"找不到学生档案：{student_id}")

        if knowledge_id not in CONCEPT_CARDS:
            raise HTTPException(status_code=404, detail=f"找不到指定考点：{knowledge_id}")

        latest_session = default_session_service.get_latest_session(student_id=student_id, knowledge_id=knowledge_id)
        effectiveness = None
        if latest_session:
            effectiveness = default_effectiveness_analyzer.analyze_session(latest_session)

        sessions = default_session_service.get_student_sessions(student_id=student_id, knowledge_id=knowledge_id)
        historical_signal = default_effectiveness_analyzer.aggregate_historical_signal(
            knowledge_id=knowledge_id,
            sessions=sessions,
            student_id=student_id,
        )

        return KnowledgeEffectivenessResponse(
            student_id=student_id,
            knowledge_id=knowledge_id,
            latest_session=latest_session,
            effectiveness=effectiveness,
            historical_signal=historical_signal,
        )


    @application.get("/api/teacher/overview", response_model=TeacherOverviewResponse)
    def get_teacher_overview_endpoint() -> TeacherOverviewResponse:
        """获取教师端只读班级宏观学情分析看板数据 (Sprint 8-C)"""
        return default_analytics_service.get_teacher_overview()

    @application.get("/api/teacher/students/{student_id}", response_model=TeacherStudentDetailResponse)
    def get_teacher_student_detail_endpoint(student_id: str) -> TeacherStudentDetailResponse:
        """获取教师端只读单名学生深度学情分析详情 (Sprint 8-C)"""
        detail = default_analytics_service.get_teacher_student_detail(student_id)
        if not detail:
            raise HTTPException(status_code=404, detail=f"找不到学生教师端分析数据：{student_id}")
        return detail

    @application.get("/api/teacher/knowledge", response_model=TeacherKnowledgeResponse)
    def get_teacher_knowledge_endpoint() -> TeacherKnowledgeResponse:
        """获取教师端 30 个考点全景分析与掌握度分布 (Sprint 10-C Phase 2)"""
        overview = default_analytics_service.get_teacher_overview()
        all_sids = [s.student_id for s in overview.students]

        kp_mastery_accum: Dict[str, List[float]] = {k: [] for k in CONCEPT_CARDS.keys()}
        kp_mistake_accum: Dict[str, int] = {k: 0 for k in CONCEPT_CARDS.keys()}

        for sid in all_sids:
            prog = default_analytics_service.get_student_progress(sid)
            if not prog:
                continue
            for kp_item in prog.knowledge_point_masteries:
                if kp_item.knowledge_id in kp_mastery_accum:
                    kp_mastery_accum[kp_item.knowledge_id].append(kp_item.mastery)

            stu_events = default_event_repository.get_events_by_student(sid)
            for se in stu_events:
                if se.event_type == "QUESTION_ATTEMPT" and se.payload.get("is_correct") is False:
                    if se.knowledge_id in kp_mistake_accum:
                        kp_mistake_accum[se.knowledge_id] += 1

        items: List[TeacherKnowledgeItem] = []
        for kid in sorted(CONCEPT_CARDS.keys()):
            card = CONCEPT_CARDS[kid]
            m_list = kp_mastery_accum.get(kid, [])
            avg_m = round(sum(m_list) / max(1, len(m_list)), 4) if m_list else 0.0
            weak_count = sum(1 for m in m_list if m < 0.60)
            mistakes = kp_mistake_accum.get(kid, 0)

            urgency = "HIGH" if weak_count >= 2 else ("MEDIUM" if weak_count == 1 else "LOW")

            items.append(
                TeacherKnowledgeItem(
                    knowledge_id=kid,
                    knowledge_name=card.knowledge_name,
                    chapter=card.chapter,
                    average_mastery=avg_m,
                    student_count=len(m_list),
                    weak_student_count=weak_count,
                    total_mistakes=mistakes,
                    urgency=urgency,
                )
            )

        return TeacherKnowledgeResponse(
            total_count=len(items),
            knowledge_points=items,
        )

    @application.get(
        "/api/teacher/knowledge/{knowledge_id}/students",
        response_model=TeacherKnowledgeDiagnosisResponse,
    )
    def get_teacher_knowledge_students_endpoint(
        knowledge_id: str,
    ) -> TeacherKnowledgeDiagnosisResponse:
        """获取教师端指定考点的学生学情诊断聚合列表 (Sprint 10-D Phase 3)"""
        if knowledge_id not in CONCEPT_CARDS:
            raise HTTPException(status_code=404, detail=f"未找到考点分析数据：{knowledge_id}")

        card = CONCEPT_CARDS[knowledge_id]
        overview = default_analytics_service.get_teacher_overview()

        diagnosis_students: List[TeacherDiagnosisStudentItem] = []
        total_mistakes = 0

        for st in overview.students:
            sid = st.student_id
            prog = default_analytics_service.get_student_progress(sid)
            kp_item = next(
                (
                    k
                    for k in (prog.knowledge_point_masteries if prog else [])
                    if k.knowledge_id == knowledge_id
                ),
                None,
            )
            mastery = round(kp_item.mastery, 4) if kp_item else 0.0

            # 统计该生在该考点的真实做题与错题数 (源自权威 EventRepository)
            stu_events = default_event_repository.get_events_by_student(sid)
            attempts = 0
            mistakes = 0
            for se in stu_events:
                if se.knowledge_id == knowledge_id and se.event_type == "QUESTION_ATTEMPT":
                    attempts += 1
                    if se.payload.get("is_correct") is False:
                        mistakes += 1

            total_mistakes += mistakes
            diagnosis_students.append(
                TeacherDiagnosisStudentItem(
                    student_id=st.student_id,
                    student_name=st.student_name,
                    major=st.major,
                    grade=st.grade,
                    mastery=mastery,
                    risk_level=st.risk_level,
                    attempts=attempts,
                    mistake_count=mistakes,
                )
            )

        # 确定性排序：1. 掌握度升序（薄弱优先）；2. 风险等级 (ATTENTION > NORMAL > HEALTHY)；3. 学号升序
        risk_priority = {"ATTENTION": 0, "NORMAL": 1, "HEALTHY": 2}
        diagnosis_students.sort(
            key=lambda s: (s.mastery, risk_priority.get(s.risk_level, 3), s.student_id)
        )

        m_list = [s.mastery for s in diagnosis_students]
        avg_m = round(sum(m_list) / max(1, len(m_list)), 4) if m_list else 0.0
        weak_count = sum(1 for s in diagnosis_students if s.mastery < 0.60)
        urgency = "HIGH" if weak_count >= 2 else ("MEDIUM" if weak_count == 1 else "LOW")

        return TeacherKnowledgeDiagnosisResponse(
            knowledge_id=knowledge_id,
            knowledge_name=card.knowledge_name,
            chapter=card.chapter,
            average_mastery=avg_m,
            student_count=len(diagnosis_students),
            weak_student_count=weak_count,
            total_mistakes=total_mistakes,
            urgency=urgency,
            students=diagnosis_students,
        )

    @application.get("/api/teacher/students", response_model=List[TeacherStudentSummary])
    def get_teacher_students_endpoint() -> List[TeacherStudentSummary]:
        """获取教师端全班学生花名册与学情摘要列表 (Sprint 10-C Phase 2)"""
        overview = default_analytics_service.get_teacher_overview()
        return overview.students

    @application.get("/api/learning/retention/{student_id}/{knowledge_id}", response_model=RetentionProfile)
    def get_retention_profile_endpoint(student_id: str, knowledge_id: str) -> RetentionProfile:
        """获取指定学生在指定考点的学习保持度档案与间隔复习建议 (Sprint 9-F)"""
        student_info = default_companion_service.context_builder.resolve_student(student_id)
        if not student_info:
            raise HTTPException(status_code=404, detail=f"找不到学生档案：{student_id}")

        if knowledge_id not in CONCEPT_CARDS:
            raise HTTPException(status_code=404, detail=f"找不到指定考点：{knowledge_id}")

        return default_retention_analyzer.analyze(student_id=student_id, knowledge_id=knowledge_id)

    @application.get("/api/learning/today/{student_id}", response_model=TodayActionResponse)
    def get_today_learning_action_endpoint(student_id: str) -> TodayActionResponse:
        """获取指定学生今日唯一的最佳学习行动建议 (Sprint 9-G)"""
        student_info = default_companion_service.context_builder.resolve_student(student_id)
        if not student_info:
            raise HTTPException(status_code=404, detail=f"找不到学生档案：{student_id}")

        try:
            return default_today_action_resolver.resolve(student_id=student_id)
        except KeyError:
            raise HTTPException(status_code=404, detail=f"找不到学生档案：{student_id}")

    # ==============================================================================
    # 教师轻量教学动作循环端点 (Sprint 10-D Phase 4: Teacher Action Loop)
    # ==============================================================================

    @application.post(
        "/api/teacher/students/{student_id}/actions",
        response_model=TeacherActionItem,
    )
    def post_teacher_action_endpoint(
        student_id: str,
        req: TeacherActionCreateRequest,
    ) -> TeacherActionItem:
        """教师发起轻量教学动作 (Sprint 10-D Phase 4)"""
        student_info = default_companion_service.context_builder.resolve_student(student_id)
        if not student_info:
            raise HTTPException(status_code=404, detail=f"找不到指定学生：{student_id}")

        if req.knowledge_id not in CONCEPT_CARDS:
            raise HTTPException(status_code=404, detail=f"找不到指定考点：{req.knowledge_id}")

        # teacher_id 严格使用服务端固定的 Demo Teacher Context "T001"
        record = active_teacher_action_repo.record_action(
            student_id=student_id,
            knowledge_id=req.knowledge_id,
            action_type=req.action_type,
            teacher_id="T001",
        )
        card = CONCEPT_CARDS[req.knowledge_id]
        return TeacherActionItem(
            action_id=record.action_id,
            teacher_id=record.teacher_id,
            student_id=record.student_id,
            knowledge_id=record.knowledge_id,
            knowledge_name=card.knowledge_name,
            action_type=record.action_type,
            created_at=record.created_at,
        )

    @application.get(
        "/api/teacher/students/{student_id}/actions",
        response_model=TeacherActionHistoryResponse,
    )
    def get_teacher_student_actions_endpoint(
        student_id: str,
    ) -> TeacherActionHistoryResponse:
        """获取教师端指定学生的所有历史教学动作流水 (Sprint 10-D Phase 4)"""
        student_info = default_companion_service.context_builder.resolve_student(student_id)
        if not student_info:
            raise HTTPException(status_code=404, detail=f"找不到指定学生：{student_id}")

        return active_teacher_action_repo.get_teacher_action_history(student_id)

    @application.get(
        "/api/students/{student_id}/teacher-actions",
        response_model=StudentRecommendationsResponse,
    )
    def get_student_teacher_actions_endpoint(
        student_id: str,
    ) -> StudentRecommendationsResponse:
        """获取学生端可消费的教师轻量学习建议列表 (Sprint 10-D Phase 4)"""
        student_info = default_companion_service.context_builder.resolve_student(student_id)
        if not student_info:
            raise HTTPException(status_code=404, detail=f"找不到指定学生：{student_id}")

        return active_teacher_action_repo.get_student_recommendations(student_id)

    # 挂载核心业务应用为子路由兜底
    application.mount("/", app_main)

    return application


app = create_gateway_app()
