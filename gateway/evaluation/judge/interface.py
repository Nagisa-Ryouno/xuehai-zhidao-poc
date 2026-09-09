# -*- coding: utf-8 -*-
"""
gateway.evaluation.judge.interface
学海智导 (Xuehai Zhidao) V2 - Phase 3 / Sprint 7-D
Stage G2: LLM Judge 抽象接口契约

设计原则：
1. 依赖倒置：上层评估流水线仅依赖 LLMJudge 抽象，与底层具体实现或网络解耦
2. 纯观察者边界：只读接收上下文与回答，绝不修改输入对象，绝无学习决策权
3. 能力声明：每个实现必须显式声明 JudgeCapabilities，明确离线与确定性边界
"""

from abc import ABC, abstractmethod

from gateway.evaluation.judge.models import JudgeCapabilities, JudgeResult
from gateway.models import LearningPromptContext, StructuredAIResponse


class LLMJudge(ABC):
    """
    LLM Judge 抽象接口基类 (Evaluation Observer)
    """

    @abstractmethod
    def evaluate(
        self,
        context: LearningPromptContext,
        response: StructuredAIResponse,
    ) -> JudgeResult:
        """
        对候选 AI 回答进行高阶语义质量与教学价值评估
        
        @param context 只读的学情提示词上下文
        @param response 待评估的候选 AI 结构化回答
        @return JudgeResult 结构化评估结果
        """
        pass

    @abstractmethod
    def capabilities(self) -> JudgeCapabilities:
        """
        获取当前 Judge 实现的能力与元数据声明
        """
        pass
