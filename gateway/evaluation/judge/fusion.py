# -*- coding: utf-8 -*-
"""
gateway.evaluation.judge.fusion
学海智导 (Xuehai Zhidao) V2 - Phase 3 / Sprint 7-D
Stage G2: Evaluation Fusion Engine (评估融合裁决引擎)

融合决策规则矩阵 (Rules 1 ~ 5)：
Rule 1 [Policy Hard Gate]:
  若 G1 策略合规性未通过 (policy_compliant == False) -> 强制 REJECT，final_valid = False。
  任何 Judge 评分均无权覆盖安全策略违规！

Rule 2 [Fact Hard Gate]:
  若 G1 事实一致性未通过 (factual_consistency == False) -> 强制 REJECT，final_valid = False。
  任何 Judge 评分均无权覆盖事实幻觉与虚构数据！

Rule 3 [Deterministic Base Failures]:
  若 G1 综合判定未通过 (deterministic_valid == False) -> 强制 REJECT，final_valid = False。

Rule 4 [Deterministic Pass + Judge Evaluation]:
  在 G1 确定性底座全部通过的前提下：
  - 若 Judge 正常返回：
    - overall_score >= 0.80 且 confidence >= 0.70 -> ACCEPT (final_valid = True)
    - 0.60 <= overall_score < 0.80 或 confidence < 0.70 -> REVIEW (final_valid = False，需人工复核)
    - overall_score < 0.60 -> REJECT (final_valid = False)
  - 若 Judge 不可用 (超时/离线/故障)：
    - 因 G1 确定性底座已完全过关，安全降级至 REVIEW (final_valid = False，标记需复核，绝不无故拒绝)

Rule 5 [安全至上与确定性]:
  相同输入融合永远产生相同决策，纯函数零副作用。
"""

from typing import List, Optional

from gateway.evaluation.judge.models import (
    FinalEvaluationResult,
    JudgeDecision,
    JudgeFailureClass,
    JudgeResult,
)
from gateway.evaluation.models import SemanticValidationResult


class EvaluationFusionEngine:
    """
    语义校验与多维 Judge 融合决策引擎
    """

    def __init__(
        self,
        accept_score_threshold: float = 0.80,
        review_score_threshold: float = 0.60,
        confidence_threshold: float = 0.70,
    ):
        self.accept_score_threshold = accept_score_threshold
        self.review_score_threshold = review_score_threshold
        self.confidence_threshold = confidence_threshold

    def fuse(
        self,
        deterministic_result: SemanticValidationResult,
        judge_result: Optional[JudgeResult] = None,
        judge_failure: JudgeFailureClass = JudgeFailureClass.NONE,
    ) -> FinalEvaluationResult:
        """
        根据严格分层决策矩阵执行多源评估融合

        @param deterministic_result G1 确定性校验结果
        @param judge_result 可选的 G2 Judge 结构化输出
        @param judge_failure Judge 执行状态
        @return FinalEvaluationResult 综合判定结果信封
        """
        violations: List[str] = list(deterministic_result.violations)

        # -------------------------------------------------------------
        # Rule 1: Policy Hard Gate 绝对阻断
        # -------------------------------------------------------------
        if not deterministic_result.policy_compliant:
            return FinalEvaluationResult(
                decision=JudgeDecision.REJECT,
                final_valid=False,
                deterministic_valid=False,
                policy_compliant=False,
                factual_consistency=deterministic_result.factual_consistency,
                deterministic_scores=deterministic_result.scores,
                judge_used=False,
                judge_result=None,
                judge_failure_class=judge_failure,
                rationale="[POLICY_HARD_GATE] 命中山河红线或越权学习决策指令，强制拒绝，LLM Judge 绝无权干预。",
                violations=violations,
            )

        # -------------------------------------------------------------
        # Rule 2: Fact Hard Gate 事实一致性阻断
        # -------------------------------------------------------------
        if not deterministic_result.factual_consistency:
            return FinalEvaluationResult(
                decision=JudgeDecision.REJECT,
                final_valid=False,
                deterministic_valid=False,
                policy_compliant=True,
                factual_consistency=False,
                deterministic_scores=deterministic_result.scores,
                judge_used=False,
                judge_result=None,
                judge_failure_class=judge_failure,
                rationale="[FACT_HARD_GATE] 存在掌握度幻觉、虚假达标线或虚构统计数据，强制拒绝。",
                violations=violations,
            )

        # -------------------------------------------------------------
        # Rule 3: G1 其它确定性校验失败 (如空内容、脱线话题、极度空泛)
        # -------------------------------------------------------------
        if not deterministic_result.valid:
            return FinalEvaluationResult(
                decision=JudgeDecision.REJECT,
                final_valid=False,
                deterministic_valid=False,
                policy_compliant=True,
                factual_consistency=deterministic_result.factual_consistency,
                deterministic_scores=deterministic_result.scores,
                judge_used=False,
                judge_result=None,
                judge_failure_class=judge_failure,
                rationale=f"[DETERMINISTIC_REJECT] 基础确定性维度未达标 ({', '.join(deterministic_result.violations)})。",
                violations=violations,
            )

        # -------------------------------------------------------------
        # Rule 4: G1 确定性底座全部通过 -> 引入 Judge 综合裁决
        # -------------------------------------------------------------
        # 4.1 Judge 可用且成功返回
        if judge_result is not None and judge_failure == JudgeFailureClass.NONE:
            if judge_result.violations:
                for jv in judge_result.violations:
                    if jv not in violations:
                        violations.append(jv)

            score = judge_result.overall_score
            conf = judge_result.confidence

            # 高分且高置信度 -> ACCEPT
            if score >= self.accept_score_threshold and conf >= self.confidence_threshold:
                return FinalEvaluationResult(
                    decision=JudgeDecision.ACCEPT,
                    final_valid=True,
                    deterministic_valid=True,
                    policy_compliant=True,
                    factual_consistency=True,
                    deterministic_scores=deterministic_result.scores,
                    judge_used=True,
                    judge_result=judge_result,
                    judge_failure_class=JudgeFailureClass.NONE,
                    rationale=f"[ACCEPT] G1 确定性底座完好，Judge 综合评分达标 ({score:.2f} >= {self.accept_score_threshold:.2f}, 置信度 {conf:.2f})。",
                    violations=violations,
                )

            # 中等分数或低置信度 -> REVIEW
            elif score >= self.review_score_threshold:
                if conf < self.confidence_threshold:
                    rat = f"[REVIEW] G1 通过且评分良好 ({score:.2f})，但 Judge 置信度不足 ({conf:.2f} < {self.confidence_threshold:.2f})，转入人工复核。"
                else:
                    rat = f"[REVIEW] G1 通过，但回答解释深度或教学表现中等 ({score:.2f} < {self.accept_score_threshold:.2f})，标记人工复核。"
                return FinalEvaluationResult(
                    decision=JudgeDecision.REVIEW,
                    final_valid=False,
                    deterministic_valid=True,
                    policy_compliant=True,
                    factual_consistency=True,
                    deterministic_scores=deterministic_result.scores,
                    judge_used=True,
                    judge_result=judge_result,
                    judge_failure_class=JudgeFailureClass.NONE,
                    rationale=rat,
                    violations=violations,
                )

            # 评分低于合格阈值 -> REJECT
            else:
                return FinalEvaluationResult(
                    decision=JudgeDecision.REJECT,
                    final_valid=False,
                    deterministic_valid=True,
                    policy_compliant=True,
                    factual_consistency=True,
                    deterministic_scores=deterministic_result.scores,
                    judge_used=True,
                    judge_result=judge_result,
                    judge_failure_class=JudgeFailureClass.NONE,
                    rationale=f"[REJECT] Judge 教学质量综合评分不足 ({score:.2f} < {self.review_score_threshold:.2f})，予以拒绝。",
                    violations=violations,
                )

        # 4.2 Judge 不可用或异常故障时的降级回退
        else:
            violations.append(f"JUDGE_FAILURE:{judge_failure.value}")
            return FinalEvaluationResult(
                decision=JudgeDecision.REVIEW,
                final_valid=False,
                deterministic_valid=True,
                policy_compliant=True,
                factual_consistency=True,
                deterministic_scores=deterministic_result.scores,
                judge_used=False,
                judge_result=None,
                judge_failure_class=judge_failure,
                rationale=f"[REVIEW_DEGRADED] G1 确定性校验已全部通过，但辅助 Judge 不可用 ({judge_failure.value})，平稳降级至人工复核。",
                violations=violations,
            )
