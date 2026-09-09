# -*- coding: utf-8 -*-
"""
gateway.evaluation.shadow.recorder
学海智导 (Xuehai Zhidao) V2 - Phase 3 / Sprint 7-D
Stage G3 Checkpoint 3: Shadow Evaluation Recorder (旁路记录器)
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from gateway.evaluation.shadow.models import ShadowEvaluationRecord


class ShadowEvaluationRecorder:
    """
    Shadow 评估专用只读旁路记录器
    仅作为 Telemetry 与 Observation 容器，纯内存暂存，绝无业务状态副作用。
    """

    def __init__(self):
        self._records: List[ShadowEvaluationRecord] = []

    def record(
        self,
        case_id: str,
        g1_result: Dict[str, Any],
        judge_result: Optional[Dict[str, Any]],
        fusion_result: Dict[str, Any],
        judge_provider: str,
        judge_model: str,
        prompt_version: str = "g3.0",
        rubric_version: str = "g3.0",
        latency_ms: float = 0.0,
        failure_class: str = "NONE",
        timestamp: Optional[str] = None,
    ) -> ShadowEvaluationRecord:
        """
        捕获一次 Shadow 评测记录
        """
        ts = timestamp or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

        record = ShadowEvaluationRecord(
            case_id=case_id,
            g1_result=g1_result,
            judge_result=judge_result,
            fusion_result=fusion_result,
            judge_provider=judge_provider,
            judge_model=judge_model,
            prompt_version=prompt_version,
            rubric_version=rubric_version,
            latency_ms=round(latency_ms, 2),
            failure_class=failure_class,
            timestamp=ts,
        )
        self._records.append(record)
        return record

    def get_records(self) -> List[ShadowEvaluationRecord]:
        return list(self._records)

    def count(self) -> int:
        return len(self._records)

    def clear(self) -> None:
        self._records.clear()
