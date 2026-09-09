# -*- coding: utf-8 -*-
"""
gateway.evaluation.judge.adapter
学海智导 (Xuehai Zhidao) V2 - Phase 3 / Sprint 7-D
Stage G2: Provider 独立 JudgeAdapter (故障隔离与异常防御)

核心原则：
1. 故障隔离：LLM Judge 属于可插拔辅助观察器，其执行抛错、超时或畸形数据绝不可崩溃评估流水线
2. 细粒度分类：通过 JudgeFailureClass 对故障场景进行结构化归类
3. 安全兜底降级：在 Judge 故障时提供防御性降级结果，并将决策平稳移交 Fusion Engine
"""

import logging
from typing import Optional, Tuple

from gateway.evaluation.judge.fake import FakeLLMJudge
from gateway.evaluation.judge.interface import LLMJudge
from gateway.evaluation.judge.models import JudgeFailureClass, JudgeResult
from gateway.models import LearningPromptContext, StructuredAIResponse

logger = logging.getLogger("xuehai.gateway.evaluation.judge")


class JudgeAdapter:
    """
    通用 Judge 适配器容器
    """

    def __init__(self, judge: Optional[LLMJudge] = None):
        self.judge = judge if judge is not None else FakeLLMJudge()

    def evaluate_safe(
        self,
        context: LearningPromptContext,
        response: StructuredAIResponse,
    ) -> Tuple[Optional[JudgeResult], JudgeFailureClass]:
        """
        在安全容错保护下调用底层 Judge

        @param context 学情上下文
        @param response 候选回答
        @return (JudgeResult | None, JudgeFailureClass)
        """
        try:
            result = self.judge.evaluate(context, response)

            # 校验结构合法性
            if not isinstance(result, JudgeResult):
                logger.warning("Judge returned non-JudgeResult instance")
                return None, JudgeFailureClass.JUDGE_BAD_RESPONSE

            if not (0.0 <= result.overall_score <= 1.0) or not (0.0 <= result.confidence <= 1.0):
                logger.warning("Judge scores out of valid [0.0, 1.0] range")
                return None, JudgeFailureClass.JUDGE_BAD_RESPONSE

            return result, JudgeFailureClass.NONE

        except TimeoutError:
            logger.error("Judge execution timed out")
            return None, JudgeFailureClass.JUDGE_TIMEOUT
        except ConnectionError:
            logger.error("Judge upstream unavailable")
            return None, JudgeFailureClass.JUDGE_UNAVAILABLE
        except ValueError as ve:
            logger.error(f"Judge bad response value: {ve}")
            return None, JudgeFailureClass.JUDGE_BAD_RESPONSE
        except Exception as e:
            logger.error(f"Judge unexpected internal error: {type(e).__name__}: {str(e)}")
            return None, JudgeFailureClass.JUDGE_INTERNAL_ERROR
