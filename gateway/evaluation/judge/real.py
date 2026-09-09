# -*- coding: utf-8 -*-
"""
gateway.evaluation.judge.real
学海智导 (Xuehai Zhidao) V2 - Phase 3 / Sprint 7-D
Stage G3 / Checkpoint 2: RealLLMJudge 实现与响应解析契约

设计原则：
1. Provider-Neutral：仅依赖抽象 LLMTransport，不强绑定任何特定模型厂商 SDK
2. 版本化提示词契约：采用 JUDGE_PROMPT_VERSION = "g3.0"
3. 严格输出结构规范化：对模型原始返回进行深度防御性校验（范围 [0.0, 1.0]、缺失字段拦截、NaN/Inf 防御）
4. 零学习决策权：Prompt 明确声明只读评测观察者边界，禁止状态机控制指令
"""

import asyncio
import concurrent.futures
import json
import logging
import math
from typing import Any, Dict, List, Optional

from gateway.evaluation.judge.config import build_judge_transport
from gateway.evaluation.judge.interface import LLMJudge
from gateway.evaluation.judge.models import (
    JudgeCapabilities,
    JudgeDimension,
    JudgeResult,
)
from gateway.evaluation.judge.prompt import (
    build_evaluation_context,
    build_judge_prompt,
)
from gateway.models import LearningPromptContext, StructuredAIResponse
from gateway.transport import LLMTransport

logger = logging.getLogger("xuehai.gateway.evaluation.judge.real")

JUDGE_PROMPT_VERSION: str = "g3.0"


class RealLLMJudge(LLMJudge):
    """
    基于通用传输层的真实 LLM Judge 评测实现
    """

    def __init__(
        self,
        transport: Optional[LLMTransport] = None,
        model: str = "deepseek-chat",
        timeout_ms: int = 5000,
        judge_version: str = "judge-v1.0",
    ):
        self.transport = transport if transport is not None else build_judge_transport()
        self.model = model
        self.timeout_ms = timeout_ms
        self.judge_version = judge_version

    def capabilities(self) -> JudgeCapabilities:
        """声明当前真实 Judge 的能力与元数据契约"""
        return JudgeCapabilities(
            supported_dimensions=[
                JudgeDimension.EXPLANATION_DEPTH,
                JudgeDimension.PEDAGOGICAL_QUALITY,
                JudgeDimension.CONTEXTUAL_RELEVANCE,
                JudgeDimension.ACTIONABILITY,
                JudgeDimension.CLARITY,
                JudgeDimension.EMPATHY,
            ],
            deterministic=False,
            network_required=True,
            provider_name="real-llm-judge",
            version=self.judge_version,
        )

    def _sync_send_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """同步桥接异步传输层，兼容已有同步评估测试流水线"""
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(
                    asyncio.run,
                    self.transport.send_payload(payload, timeout_ms=self.timeout_ms),
                )
                return future.result()
        else:
            return asyncio.run(
                self.transport.send_payload(payload, timeout_ms=self.timeout_ms)
            )

    def _extract_and_parse_json(self, raw_response: Any) -> Dict[str, Any]:
        """深度提取并解析模型原始返回中的 JSON 内容"""
        if isinstance(raw_response, str):
            try:
                return json.loads(raw_response)
            except Exception as e:
                raise ValueError(f"Failed to parse raw string response as JSON: {str(e)}")

        if not isinstance(raw_response, dict):
            raise ValueError(f"Expected dict response from transport, got: {type(raw_response)}")

        # 1. 兼容标准 OpenAI 聊天补全响应格式
        if "choices" in raw_response:
            choices = raw_response["choices"]
            if not choices or not isinstance(choices, list):
                raise ValueError("Response 'choices' list is empty or malformed")
            first_choice = choices[0]
            message = first_choice.get("message", {})
            content = message.get("content", "")
            if not content:
                raise ValueError("Response choice message content is empty")
            try:
                return json.loads(content)
            except Exception as e:
                raise ValueError(f"Failed to parse LLM message content as JSON: {str(e)}")

        # 2. 兼容已直接解包好的 JSON 字典
        return raw_response

    def _validate_score(self, val: Any, field_name: str) -> float:
        """严格校验评分数值边界，拦截非法类型、NaN、Inf 与越界值"""
        if val is None:
            raise ValueError(f"Missing required score field: '{field_name}'")
        try:
            score = float(val)
        except (ValueError, TypeError):
            raise ValueError(f"Field '{field_name}' must be a float, got: {val}")

        if math.isnan(score) or math.isinf(score):
            raise ValueError(f"Field '{field_name}' cannot be NaN or Infinity")

        if not (0.0 <= score <= 1.0):
            raise ValueError(f"Field '{field_name}' out of bounds [0.0, 1.0], got: {score}")

        return score

    def evaluate(
        self,
        context: LearningPromptContext,
        response: StructuredAIResponse,
    ) -> JudgeResult:
        """
        执行候选 AI 回答的高阶教学质量评估
        """
        # 1. 构建提示词文本（内部执行 PII 与敏感信息剥离）
        prompt_text = build_judge_prompt(context, response, model=self.model)

        system_instruction = (
            "You are an independent AI Evaluation Observer in the Xuehai Zhidao adaptive learning system. "
            "You evaluate the pedagogical and explanation quality of candidate AI learning companion responses. "
            "You have ZERO learning decision authority. You cannot modify learning states."
        )

        payload = {
            "model": self.model,
            "system_prompt": system_instruction,
            "user_prompt": prompt_text,
            "temperature": 0.0,
            "response_format": {"type": "json_object"},
        }

        # 2. 调用传输层发送网络载荷
        raw_response = self._sync_send_payload(payload)

        # 3. 提取并解析 JSON
        parsed = self._extract_and_parse_json(raw_response)

        # 4. 强类型字段检验与清洗
        overall_score = self._validate_score(parsed.get("overall_score"), "overall_score")
        confidence = self._validate_score(parsed.get("confidence"), "confidence")

        # 维度评分检验
        dim_scores_raw = parsed.get("dimension_scores", {})
        if not isinstance(dim_scores_raw, dict):
            raise ValueError("Field 'dimension_scores' must be a dictionary")

        clean_dim_scores: Dict[str, float] = {}
        for dim_k, dim_v in dim_scores_raw.items():
            clean_dim_scores[str(dim_k)] = self._validate_score(dim_v, f"dimension_scores.{dim_k}")

        # 评语摘要提取
        rationale = (
            parsed.get("rationale_summary")
            or parsed.get("reasoning")
            or parsed.get("rationale")
            or "No detailed rationale provided."
        )
        if not isinstance(rationale, str):
            rationale = str(rationale)

        # 违规标签清洗
        violations_raw = parsed.get("violations", [])
        if not isinstance(violations_raw, list):
            violations_raw = []
        violations = [str(v) for v in violations_raw]

        # 基础质量达标布尔初判
        valid_val = parsed.get("valid")
        if isinstance(valid_val, bool):
            valid = valid_val
        else:
            valid = bool(overall_score >= 0.60)

        return JudgeResult(
            judge_version=self.judge_version,
            valid=valid,
            overall_score=overall_score,
            confidence=confidence,
            dimension_scores=clean_dim_scores,
            rationale_summary=rationale,
            violations=violations,
        )
