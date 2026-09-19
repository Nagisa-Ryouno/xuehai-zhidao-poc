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

强制边界保障：若候选 ID 未在当前上下文候选池中提供（例如 K03 -> R999），坚决 REJECT。
"""

import json
import re
from typing import Any, Dict, List, Optional, Union
from pydantic import ValidationError

from gateway.adapter import ProviderException
from gateway.content.concept_cards import CONCEPT_CARDS
from gateway.learning.resources.service import get_unified_resource_by_id
from gateway.ai.recommendation.models import (
    RECOMMENDATION_FORBIDDEN_FIELDS,
    RecommendationCandidate,
    RecommendationContext,
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


# 明显危险的命令注入或系统覆写特征 (非脆弱事实判断，仅防御危险指令渗透)
_DANGEROUS_REASON_PATTERNS = [
    re.compile(r"(?:DROP\s+TABLE|SELECT\s+.*FROM|INSERT\s+INTO|DELETE\s+FROM)", re.IGNORECASE),
    re.compile(r"(?:<script>|javascript:|system\(|os\.system)", re.IGNORECASE),
    re.compile(r"(?:set_mastery|bkt_update|mutate_path|unlock_nodes|修改掌握度|设置掌握度|将掌握度设为|强行解锁|强行锁定)", re.IGNORECASE),
]


class RecommendationValidator:
    """确定性推荐校验器"""

    @classmethod
    def validate(
        cls,
        raw_output: Union[str, Dict[str, Any]],
        context: Optional[RecommendationContext] = None,
        max_allowed: int = 3,
    ) -> List[ValidatedRecommendation]:
        """
        全量执行 Layer 1 ~ Layer 3 校验。
        校验通过后，由系统注入权威元数据 (title, resource_type, source) 返回 ValidatedRecommendation 列表。
        任何一项不合规，坚决抛出 ValidationRejectedError 触发安全阻断。
        """
        # ======================================================================
        # Layer 1: 语法与基本容器结构校验
        # ======================================================================
        if isinstance(raw_output, str):
            clean_str = raw_output.strip()
            # 剥离可能存在的 markdown 标记 (容错处理)
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
                raise ValidationRejectedError(f"Layer 1 Reject: Output is not valid JSON: {str(e)}", "INVALID_JSON_SYNTAX")
        elif isinstance(raw_output, dict):
            parsed = raw_output
        else:
            raise ValidationRejectedError("Layer 1 Reject: Expected JSON dict or string", "INVALID_DATA_TYPE")

        if not isinstance(parsed, dict):
            raise ValidationRejectedError("Layer 1 Reject: Root JSON must be an object", "ROOT_NOT_OBJECT")

        if "recommendations" not in parsed:
            raise ValidationRejectedError("Layer 1 Reject: Missing required 'recommendations' key", "MISSING_RECOMMENDATIONS_KEY")

        raw_recs = parsed["recommendations"]
        if not isinstance(raw_recs, list):
            raise ValidationRejectedError("Layer 1 Reject: 'recommendations' must be a list", "RECOMMENDATIONS_NOT_LIST")

        if len(raw_recs) > max_allowed:
            raise ValidationRejectedError(
                f"Layer 1 Reject: Too many recommendations ({len(raw_recs)} > {max_allowed})",
                "TOO_MANY_RECOMMENDATIONS",
            )

        # ======================================================================
        # Layer 2: 越权生产决策字段与结构安全性扫描
        # ======================================================================
        # 扫描顶层禁止字段 (即使 recommendations 为空，包含禁止字段也必须拦截)
        for k in parsed.keys():
            if k in RECOMMENDATION_FORBIDDEN_FIELDS:
                raise ValidationRejectedError(
                    f"Layer 2 Reject: Forbidden decision field detected at root: '{k}'",
                    "FORBIDDEN_FIELD_ROOT",
                )

        # 空列表为合法安全输出 (AI 判断当前无可推荐内容)
        if len(raw_recs) == 0:
            return []

        validated_candidates: List[RecommendationCandidate] = []
        for idx, item in enumerate(raw_recs):
            if not isinstance(item, dict):
                raise ValidationRejectedError(
                    f"Layer 2 Reject: Item #{idx} in recommendations is not a dict",
                    "ITEM_NOT_DICT",
                )

            # 扫描 item 内部禁止字段
            for field in item.keys():
                if field in RECOMMENDATION_FORBIDDEN_FIELDS:
                    raise ValidationRejectedError(
                        f"Layer 2 Reject: Forbidden decision field detected in item #{idx}: '{field}'",
                        "FORBIDDEN_FIELD_ITEM",
                    )

            # Pydantic 严格白名单校验 (extra='forbid')
            try:
                candidate = RecommendationCandidate(**item)
            except ValidationError as ve:
                raise ValidationRejectedError(
                    f"Layer 2 Reject: Schema validation failed for item #{idx}: {str(ve)}",
                    "SCHEMA_VALIDATION_FAILED",
                )

            # 校验 reason 合规性 (非空、有界、防注入)
            reason_text = candidate.reason.strip()
            if not reason_text:
                raise ValidationRejectedError(f"Layer 2 Reject: Empty reason in item #{idx}", "EMPTY_REASON")
            if len(reason_text) > 300:
                raise ValidationRejectedError(f"Layer 2 Reject: Reason too long ({len(reason_text)} > 300) in item #{idx}", "REASON_TOO_LONG")

            for pat in _DANGEROUS_REASON_PATTERNS:
                if pat.search(reason_text):
                    raise ValidationRejectedError(
                        f"Layer 2 Reject: Reason contains disallowed command/mutation syntax in item #{idx}",
                        "MALICIOUS_REASON_INJECTION",
                    )

            validated_candidates.append(candidate)

        # ======================================================================
        # Layer 3: 上下文事实锚定与系统真实性校验 (Context Grounding)
        # ======================================================================
        # 构建 Context 允许的白名单索引集合
        context_kids = set()
        context_rids = set()
        context_kid_rid_pairs = set()

        if context:
            for k in context.knowledge_states:
                context_kids.add(k.knowledge_id)
            for r in context.resources:
                context_kids.add(r.knowledge_id)
                context_rids.add(r.resource_id)
                context_kid_rid_pairs.add((r.knowledge_id, r.resource_id))

        final_recommendations: List[ValidatedRecommendation] = []
        for idx, cand in enumerate(validated_candidates):
            kid = cand.knowledge_id
            rid = cand.resource_id

            # 1. 考点真实存在性
            if kid not in CONCEPT_CARDS:
                raise ValidationRejectedError(
                    f"Layer 3 Reject: Knowledge ID '{kid}' does not exist in authoritative concept cards",
                    "UNKNOWN_KNOWLEDGE_ID",
                )

            # 2. 资源真实存在性 (查询统一目录)
            resource_obj = get_unified_resource_by_id(rid)
            if not resource_obj:
                raise ValidationRejectedError(
                    f"Layer 3 Reject: Resource ID '{rid}' does not exist in authoritative catalog",
                    "UNKNOWN_RESOURCE_ID",
                )

            # 3. 资源考点一致性
            if resource_obj.knowledge_id != kid:
                raise ValidationRejectedError(
                    f"Layer 3 Reject: Resource '{rid}' belongs to '{resource_obj.knowledge_id}', not '{kid}'",
                    "RESOURCE_KNOWLEDGE_MISMATCH",
                )

            # 4. 上下文候选池严格隔离 (Context Grounding 强制边界)
            # 若提供了 Context，候选 ID 与配对关系必须严格存在于本次 Context 中
            if context:
                if kid not in context_kids:
                    raise ValidationRejectedError(
                        f"Layer 3 Reject: Knowledge '{kid}' not in supplied context",
                        "KNOWLEDGE_NOT_IN_CONTEXT",
                    )
                if rid not in context_rids:
                    raise ValidationRejectedError(
                        f"Layer 3 Reject: Resource '{rid}' not in supplied context candidates",
                        "RESOURCE_NOT_IN_CONTEXT",
                    )
                if (kid, rid) not in context_kid_rid_pairs:
                    raise ValidationRejectedError(
                        f"Layer 3 Reject: Pair ({kid}, {rid}) not present in supplied context candidate set",
                        "PAIR_NOT_IN_CONTEXT",
                    )

            # 5. 系统填充权威元数据 (由系统保证真实性，绝不依赖 AI 拟造)
            res_type_str = (
                resource_obj.resource_type.value
                if hasattr(resource_obj.resource_type, "value")
                else str(resource_obj.resource_type)
            )
            final_recommendations.append(
                ValidatedRecommendation(
                    knowledge_id=kid,
                    resource_id=rid,
                    reason=cand.reason,
                    title=resource_obj.title,
                    resource_type=res_type_str,
                    source=resource_obj.source,
                )
            )

        return final_recommendations
