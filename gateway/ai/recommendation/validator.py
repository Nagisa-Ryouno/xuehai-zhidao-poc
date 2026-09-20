# -*- coding: utf-8 -*-
"""
gateway.ai.recommendation.validator
===================================
学海智导 (Xuehai Zhidao) — Phase 6 / Sprint 10-B / Phase 2
确定性推荐校验器 (Deterministic Recommendation Validator)

三层防御安全架构：
Layer 1: Schema 校验 (合法 JSON 字典, recommendations 列表, 0 <= 长度 <= 3)；
Layer 2: 结构安全性校验 (严禁 FORBIDDEN_DECISION_FIELDS, 严禁指令/代码注入, extra='forbid')；
Layer 3: 上下文事实锚定校验 (Context Grounding):
         - candidate.knowledge_id 必须存在于 Context 中；
         - candidate.resource_id 必须存在于 Context 中；
         - candidate (knowledge_id, resource_id) 匹配对必须存在于 Context 中；
         - resource.knowledge_id 必须等于 candidate.knowledge_id；
         - 考点必须存在于 CONCEPT_CARDS，资源必须存在于 Unified Resource Catalog。

确定性策略与红线保障：
1. 确定性排序：校验通过的候选按 (knowledge_id, resource_id) 升序稳定仲裁，AI 输出顺序、rank、priority 绝对不参与排序；
2. 结构化拒绝：未通过校验的项记录为自包含的 RejectedCandidate(candidate, code, reason)；
3. 重复项去重：同一 (knowledge_id, resource_id) 重复出现时，首项保留，第二项记录为 DUPLICATE_CANDIDATE；
4. 强制边界保障：若候选 ID 未在当前上下文候选池中提供（例如 K03 -> R999），即使全局资源库存在，也坚决 REJECT。
"""

import json
import re
from typing import Any, Dict, List, Optional, Set, Union
from pydantic import ValidationError

from gateway.adapter import ProviderException
from gateway.content.concept_cards import CONCEPT_CARDS
from gateway.learning.resources.service import get_unified_resource_by_id
from gateway.ai.recommendation.models import (
    RECOMMENDATION_FORBIDDEN_FIELDS,
    CandidateValidationResult,
    RecommendationCandidate,
    RecommendationContext,
    RejectedCandidate,
    ValidatedRecommendation,
)


class ValidationRejectedError(ProviderException):
    """确定性校验器拦截异常 (声明受控阻断原因)"""

    def __init__(self, message: str, rejection_code: str = "VALIDATION_REJECTED"):
        super().__init__(message)
        self.message = message
        self.rejection_code = rejection_code

    def __repr__(self) -> str:
        return f"ValidationRejectedError(code={self.rejection_code}, message={self.message})"


# 明显危险的命令注入或系统覆写特征 (防御结构化指令渗透，避免自然语言误杀)
_DANGEROUS_REASON_PATTERNS = [
    re.compile(r"(?:DROP\s+TABLE|SELECT\s+.*FROM|INSERT\s+INTO|DELETE\s+FROM)", re.IGNORECASE),
    re.compile(r"(?:<script>|javascript:|system\(|os\.system)", re.IGNORECASE),
    re.compile(r"(?:set_mastery|bkt_update|mutate_path|unlock_nodes|修改掌握度|设置掌握度|将掌握度设为|强行解锁|强行锁定)", re.IGNORECASE),
]


class RecommendationValidator:
    """确定性推荐校验器"""

    @classmethod
    def validate_candidates_detailed(
        cls,
        raw_output: Union[str, Dict[str, Any]],
        context: Optional[RecommendationContext] = None,
        max_allowed: int = 3,
    ) -> CandidateValidationResult:
        """
        全量执行 Layer 1 ~ Layer 3 校验，返回自包含的 CandidateValidationResult。
        
        返回值包含：
        - validated_candidates: 通过校验并注入权威元数据、按确定性键值排序的列表；
        - rejected_candidates: 结构化记录被拦截的候选及对应拒绝码与原因；
        - validation_reasons: 拒绝原因派生汇总列表。
        """
        validated_candidates: List[ValidatedRecommendation] = []
        rejected_candidates: List[RejectedCandidate] = []

        # ======================================================================
        # Layer 1: 语法与基本容器结构校验
        # ======================================================================
        parsed: Dict[str, Any] = {}
        if isinstance(raw_output, str):
            clean_str = raw_output.strip()
            if clean_str.startswith("```json"):
                clean_str = clean_str[7:]
            if clean_str.startswith("```"):
                clean_str = clean_str[3:]
            if clean_str.endswith("```"):
                clean_str = clean_str[:-3]
            clean_str = clean_str.strip()

            try:
                parsed = json.loads(clean_str)
            except Exception as e:
                rej = RejectedCandidate(
                    candidate={"raw": str(raw_output)},
                    code="INVALID_JSON_SYNTAX",
                    reason=f"Layer 1 Reject: Output is not valid JSON: {str(e)}",
                )
                return CandidateValidationResult(
                    validated_candidates=[],
                    rejected_candidates=[rej],
                    validation_reasons=[f"{rej.code}: {rej.reason}"],
                )
        elif isinstance(raw_output, dict):
            parsed = raw_output
        else:
            rej = RejectedCandidate(
                candidate={"raw": str(raw_output)},
                code="INVALID_DATA_TYPE",
                reason="Layer 1 Reject: Expected JSON dict or string",
            )
            return CandidateValidationResult(
                validated_candidates=[],
                rejected_candidates=[rej],
                validation_reasons=[f"{rej.code}: {rej.reason}"],
            )

        if not isinstance(parsed, dict):
            rej = RejectedCandidate(
                candidate={"raw": parsed},
                code="ROOT_NOT_OBJECT",
                reason="Layer 1 Reject: Root JSON must be an object",
            )
            return CandidateValidationResult(
                validated_candidates=[],
                rejected_candidates=[rej],
                validation_reasons=[f"{rej.code}: {rej.reason}"],
            )

        # 扫描顶层禁止字段
        for k in parsed.keys():
            if k in RECOMMENDATION_FORBIDDEN_FIELDS:
                rej = RejectedCandidate(
                    candidate=parsed,
                    code="FORBIDDEN_FIELD_ROOT",
                    reason=f"Layer 2 Reject: Forbidden decision field detected at root: '{k}'",
                )
                return CandidateValidationResult(
                    validated_candidates=[],
                    rejected_candidates=[rej],
                    validation_reasons=[f"{rej.code}: {rej.reason}"],
                )

        if "recommendations" not in parsed:
            rej = RejectedCandidate(
                candidate=parsed,
                code="MISSING_RECOMMENDATIONS_KEY",
                reason="Layer 1 Reject: Missing required 'recommendations' key",
            )
            return CandidateValidationResult(
                validated_candidates=[],
                rejected_candidates=[rej],
                validation_reasons=[f"{rej.code}: {rej.reason}"],
            )

        raw_recs = parsed["recommendations"]
        if not isinstance(raw_recs, list):
            rej = RejectedCandidate(
                candidate=parsed,
                code="RECOMMENDATIONS_NOT_LIST",
                reason="Layer 1 Reject: 'recommendations' must be a list",
            )
            return CandidateValidationResult(
                validated_candidates=[],
                rejected_candidates=[rej],
                validation_reasons=[f"{rej.code}: {rej.reason}"],
            )

        if len(raw_recs) > max_allowed:
            rej = RejectedCandidate(
                candidate={"count": len(raw_recs), "max_allowed": max_allowed},
                code="TOO_MANY_RECOMMENDATIONS",
                reason=f"Layer 1 Reject: Too many recommendations ({len(raw_recs)} > {max_allowed})",
            )
            return CandidateValidationResult(
                validated_candidates=[],
                rejected_candidates=[rej],
                validation_reasons=[f"{rej.code}: {rej.reason}"],
            )

        # 空列表为合法安全输出 (AI 判定无可推荐候选)
        if len(raw_recs) == 0:
            return CandidateValidationResult(
                validated_candidates=[],
                rejected_candidates=[],
                validation_reasons=[],
            )

        # ======================================================================
        # Layer 2 & 3: 逐项校验、去重与事实锚定
        # ======================================================================
        # 提取上下文白名单索引
        context_kids: Set[str] = set()
        context_rids: Set[str] = set()
        context_kid_rid_pairs: Set[Tuple[str, str]] = set()

        if context:
            for k in context.knowledge_states:
                context_kids.add(k.knowledge_id)
            for r in context.resources:
                context_kids.add(r.knowledge_id)
                context_rids.add(r.resource_id)
                context_kid_rid_pairs.add((r.knowledge_id, r.resource_id))

        seen_pairs: Set[Tuple[str, str]] = set()

        for idx, item in enumerate(raw_recs):
            if not isinstance(item, dict):
                rejected_candidates.append(
                    RejectedCandidate(
                        candidate={"item": item, "index": idx},
                        code="ITEM_NOT_DICT",
                        reason=f"Layer 2 Reject: Item #{idx} in recommendations is not a dict",
                    )
                )
                continue

            # 1. 扫描 item 内部禁止字段 (如 rank, priority, score, mutation 指令)
            has_forbidden = False
            for field in item.keys():
                if field in RECOMMENDATION_FORBIDDEN_FIELDS or field in ("rank", "priority", "score"):
                    rejected_candidates.append(
                        RejectedCandidate(
                            candidate=item,
                            code="FORBIDDEN_FIELD_ITEM",
                            reason=f"Layer 2 Reject: Forbidden decision field detected in item #{idx}: '{field}'",
                        )
                    )
                    has_forbidden = True
                    break
            if has_forbidden:
                continue

            # 2. Pydantic extra='forbid' 结构拦截 (非禁止字段但未定义的非法参数)
            try:
                cand = RecommendationCandidate(**item)
            except ValidationError as ve:
                rejected_candidates.append(
                    RejectedCandidate(
                        candidate=item,
                        code="SCHEMA_VALIDATION_FAILED",
                        reason=f"Layer 2 Reject: Schema validation failed for item #{idx}: {str(ve)}",
                    )
                )
                continue

            # 3. 校验 reason 合规性 (非空、长度有界、防注入)
            reason_text = cand.reason.strip()
            if not reason_text:
                rejected_candidates.append(
                    RejectedCandidate(
                        candidate=item,
                        code="EMPTY_REASON",
                        reason=f"Layer 2 Reject: Empty reason in item #{idx}",
                    )
                )
                continue

            if len(reason_text) > 300:
                rejected_candidates.append(
                    RejectedCandidate(
                        candidate=item,
                        code="REASON_TOO_LONG",
                        reason=f"Layer 2 Reject: Reason too long ({len(reason_text)} > 300) in item #{idx}",
                    )
                )
                continue

            has_injection = False
            for pat in _DANGEROUS_REASON_PATTERNS:
                if pat.search(reason_text):
                    rejected_candidates.append(
                        RejectedCandidate(
                            candidate=item,
                            code="MALICIOUS_REASON_INJECTION",
                            reason=f"Layer 2 Reject: Reason contains disallowed command/mutation syntax in item #{idx}",
                        )
                    )
                    has_injection = True
                    break
            if has_injection:
                continue

            kid = cand.knowledge_id
            rid = cand.resource_id
            pair = (kid, rid)

            # 4. 去重校验 (Case E: 重复 candidate 确定性去重)
            if pair in seen_pairs:
                rejected_candidates.append(
                    RejectedCandidate(
                        candidate=item,
                        code="DUPLICATE_CANDIDATE",
                        reason=f"Layer 2 Reject: Duplicate candidate pair ({kid}, {rid}) already validated",
                    )
                )
                continue

            # 5. 考点真实性 (Case C)
            if kid not in CONCEPT_CARDS:
                rejected_candidates.append(
                    RejectedCandidate(
                        candidate=item,
                        code="UNKNOWN_KNOWLEDGE_ID",
                        reason=f"Layer 3 Reject: Knowledge ID '{kid}' does not exist in authoritative concept cards",
                    )
                )
                continue

            # 6. 资源真实性 (Case D)
            resource_obj = get_unified_resource_by_id(rid)
            if not resource_obj:
                rejected_candidates.append(
                    RejectedCandidate(
                        candidate=item,
                        code="UNKNOWN_RESOURCE_ID",
                        reason=f"Layer 3 Reject: Resource ID '{rid}' does not exist in authoritative catalog",
                    )
                )
                continue

            # 7. 资源考点归属一致性
            if resource_obj.knowledge_id != kid:
                rejected_candidates.append(
                    RejectedCandidate(
                        candidate=item,
                        code="RESOURCE_KNOWLEDGE_MISMATCH",
                        reason=f"Layer 3 Reject: Resource '{rid}' belongs to '{resource_obj.knowledge_id}', not '{kid}'",
                    )
                )
                continue

            # 8. 上下文候选池严格隔离 (Case B: Global Catalog 存在 != 当前 Context 合法)
            if context:
                if kid not in context_kids:
                    rejected_candidates.append(
                        RejectedCandidate(
                            candidate=item,
                            code="KNOWLEDGE_NOT_IN_CONTEXT",
                            reason=f"Layer 3 Reject: Knowledge '{kid}' not in supplied context",
                        )
                    )
                    continue

                if rid not in context_rids:
                    rejected_candidates.append(
                        RejectedCandidate(
                            candidate=item,
                            code="RESOURCE_NOT_IN_CONTEXT",
                            reason=f"Layer 3 Reject: Resource '{rid}' not in supplied context candidates",
                        )
                    )
                    continue

                if pair not in context_kid_rid_pairs:
                    rejected_candidates.append(
                        RejectedCandidate(
                            candidate=item,
                            code="PAIR_NOT_IN_CONTEXT",
                            reason=f"Layer 3 Reject: Pair ({kid}, {rid}) not present in supplied context candidate set",
                        )
                    )
                    continue

            # 9. 校验通过，记录已见对并注入权威元数据
            seen_pairs.add(pair)
            res_type_str = (
                resource_obj.resource_type.value
                if hasattr(resource_obj.resource_type, "value")
                else str(resource_obj.resource_type)
            )
            validated_candidates.append(
                ValidatedRecommendation(
                    knowledge_id=kid,
                    resource_id=rid,
                    reason=cand.reason,
                    title=resource_obj.title,
                    resource_type=res_type_str,
                    source=resource_obj.source,
                )
            )

        # ======================================================================
        # 确定性排序仲裁 (Order Determinism)
        # 无论 AI 以何种顺序输出，最终均按照 (knowledge_id, resource_id) 升序稳定排列
        # AI rank/priority/score 绝对不参与排序
        # ======================================================================
        validated_candidates.sort(key=lambda r: (r.knowledge_id, r.resource_id))

        validation_reasons = [f"{r.code}: {r.reason}" for r in rejected_candidates]

        return CandidateValidationResult(
            validated_candidates=validated_candidates,
            rejected_candidates=rejected_candidates,
            validation_reasons=validation_reasons,
        )

    @classmethod
    def validate(
        cls,
        raw_output: Union[str, Dict[str, Any]],
        context: Optional[RecommendationContext] = None,
        max_allowed: int = 3,
    ) -> List[ValidatedRecommendation]:
        """
        向后兼容契约：若存在任何被拒绝项，抛出首个 ValidationRejectedError；
        全部通过时返回 validated_candidates 列表。
        """
        res = cls.validate_candidates_detailed(
            raw_output=raw_output,
            context=context,
            max_allowed=max_allowed,
        )
        if res.rejected_candidates:
            first_rej = res.rejected_candidates[0]
            raise ValidationRejectedError(first_rej.reason, first_rej.code)

        return res.validated_candidates
