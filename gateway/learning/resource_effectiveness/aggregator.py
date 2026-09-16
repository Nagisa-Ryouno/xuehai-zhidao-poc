# -*- coding: utf-8 -*-
"""
gateway.learning.resource_effectiveness.aggregator
==================================================
学海智导 (Xuehai Zhidao) — Phase 5 / Sprint 9-E
资源学习效果只读聚合器 (Resource Effectiveness Aggregator)

设计规范与红线：
1. 绝对只读：严格只读取 `data/resource_effectiveness_events.jsonl`，严禁写入任何文件；
2. 零核心污染：严禁读取或修改 `data/bkt_states.json` 与 `data/learning_events.jsonl`；
3. 多生多考点严格隔离：按 (student_id, knowledge_id) 严格过滤，绝不发生跨学生、跨考点数据交叉；
4. 容错防御：空行、格式损坏、缺失 delta 的日志安全跳过，绝不抛出未捕获异常崩溃推荐服务；
5. 依赖注入：构造函数允许传入 `events_file`，方便测试用例进行物理文件级隔离测试。
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from app.core.config import settings
from gateway.learning.resource_effectiveness.models import (
    HistoricalEffectiveness,
    ResourceEffectivenessProfile,
    classify_effectiveness,
)

DEFAULT_EFFECTIVENESS_EVENTS_FILE = settings.DATA_DIR / "resource_effectiveness_events.jsonl"


def normalize_resource_type_key(raw_type: str) -> str:
    """规整化资源类型字符串键名"""
    key = str(raw_type).strip().lower()
    if key in ("practice", "micro_quiz", "quiz"):
        return "practice"
    if key in ("concept_card", "concept"):
        return "concept_card"
    if key in ("example", "example_case"):
        return "example"
    if key in ("document", "handout"):
        return "document"
    if key in ("video", "guide_video"):
        return "video"
    return key


class ResourceEffectivenessAggregator:
    """资源学习效果只读聚合器"""

    def __init__(self, events_file: Optional[Path] = None):
        self._events_file = events_file or DEFAULT_EFFECTIVENESS_EVENTS_FILE

    @property
    def events_file(self) -> Path:
        return self._events_file

    def get_resource_effectiveness(
        self,
        student_id: str,
        knowledge_id: str,
    ) -> Dict[str, ResourceEffectivenessProfile]:
        """
        聚合指定学生在指定考点下各资源类型的历史效果档案。
        返回字典支持规范大写 (CONCEPT_CARD) 与通俗小写 (concept_card, micro_quiz) 双向索引。
        """
        if not self._events_file.exists():
            return {}

        # 收集每个 resource_type 对应的 delta 序列（按时序）
        type_deltas: Dict[str, List[float]] = {}

        try:
            with open(self._events_file, "r", encoding="utf-8") as f:
                for line in f:
                    line_str = line.strip()
                    if not line_str:
                        continue
                    try:
                        record = json.loads(line_str)
                    except Exception:
                        # 容错：跳过损坏的 JSON 行
                        continue

                    # 严格过滤 student_id 与 knowledge_id
                    if record.get("student_id") != student_id:
                        continue
                    if record.get("knowledge_id") != knowledge_id:
                        continue

                    # 只分析携带 delta 的效果结算事件
                    raw_delta = record.get("delta")
                    if raw_delta is None:
                        continue
                    try:
                        delta_val = float(raw_delta)
                    except (ValueError, TypeError):
                        continue

                    metadata = record.get("metadata") or {}

                    # 提取该事件涉及的资源类型集合
                    involved_types = self._extract_resource_types(record, metadata)
                    for rt in involved_types:
                        type_deltas.setdefault(rt, []).append(delta_val)

        except Exception as err:
            # 容错：防止文件读取异常导致推荐整体崩溃
            return {}

        # 构建聚合实体字典
        result_map: Dict[str, ResourceEffectivenessProfile] = {}
        for r_type, deltas in type_deltas.items():
            count = len(deltas)
            avg_delta = round(sum(deltas) / count, 4) if count > 0 else 0.0
            last_delta = round(deltas[-1], 4) if deltas else 0.0
            eff = classify_effectiveness(usage_count=count, average_delta=avg_delta)

            profile = ResourceEffectivenessProfile(
                student_id=student_id,
                knowledge_id=knowledge_id,
                resource_type=r_type,
                usage_count=count,
                average_delta=avg_delta,
                last_delta=last_delta,
                effectiveness=eff,
            )

            # 支持多别名索引，方便调用方无感查询
            norm_key = normalize_resource_type_key(r_type)
            result_map[norm_key] = profile
            result_map[r_type] = profile
            result_map[r_type.upper()] = profile
            result_map[r_type.lower()] = profile

            if norm_key == "practice":
                result_map["micro_quiz"] = profile

        return result_map

    def _extract_resource_types(self, record: Dict[str, Any], metadata: Dict[str, Any]) -> List[str]:
        """从事件记录及其 metadata 中解析涉及的资源类型"""
        types: List[str] = []

        # 1. 直接指定单类型
        if metadata.get("resource_type"):
            types.append(str(metadata["resource_type"]))

        # 2. 直接指定多类型
        if metadata.get("resource_types") and isinstance(metadata["resource_types"], list):
            for t in metadata["resource_types"]:
                types.append(str(t))

        # 3. 记录中直接包含 resource_type
        if record.get("resource_type"):
            types.append(str(record["resource_type"]))

        # 4. 从 resource_ids / completed_resource_ids 推导
        all_rids = []
        if metadata.get("completed_resource_ids") and isinstance(metadata["completed_resource_ids"], list):
            all_rids.extend(metadata["completed_resource_ids"])
        elif metadata.get("resource_ids") and isinstance(metadata["resource_ids"], list):
            all_rids.extend(metadata["resource_ids"])

        if record.get("resource_id"):
            all_rids.append(record["resource_id"])

        for rid in all_rids:
            inferred = self._infer_type_from_id(rid)
            if inferred and inferred not in types:
                types.append(inferred)

        # 5. 若有微测验参与信息，归入 PRACTICE / micro_quiz
        if (record.get("quiz_result") is not None or metadata.get("quiz_question_id")) and "PRACTICE" not in types:
            types.append("PRACTICE")

        return types

    @staticmethod
    def _infer_type_from_id(resource_id: str) -> Optional[str]:
        """根据标准资源ID后缀快速推导资源类型"""
        rid = str(resource_id).lower()
        if "_concept" in rid:
            return "CONCEPT_CARD"
        elif "_example" in rid:
            return "EXAMPLE"
        elif "_practice" in rid or "_quiz" in rid:
            return "PRACTICE"
        elif "_document" in rid:
            return "DOCUMENT"
        elif "_video" in rid:
            return "VIDEO"
        return None


default_resource_effectiveness_aggregator = ResourceEffectivenessAggregator()
