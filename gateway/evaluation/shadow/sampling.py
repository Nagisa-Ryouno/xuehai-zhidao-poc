# -*- coding: utf-8 -*-
"""
gateway.evaluation.shadow.sampling
学海智导 (Xuehai Zhidao) V2 - Phase 3 / Sprint 7-D
Stage G4: Shadow Sampling Policy (旁路评估采样策略)

设计原则：
1. 默认安全关闭：sample_rate=0.0，未经配置时 100% 不采样
2. 完全确定性：基于 SHA-256 稳定哈希或固定种子，相同输入永远产生相同采样决策
3. 严格无副作用：纯只读判断，绝不修改内部状态
"""

import hashlib
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class ShadowSamplingPolicy(BaseModel):
    """
    Shadow 旁路评测采样策略契约
    """
    model_config = ConfigDict(extra="forbid")

    sample_rate: float = Field(
        default=0.0, ge=0.0, le=1.0, description="采样比率 [0.0, 1.0]，默认 0.0 完全关闭"
    )
    max_cases: Optional[int] = Field(
        default=None, gt=0, description="最大采样用例数上限"
    )
    category_allowlist: Optional[List[str]] = Field(
        default=None, description="允许采样的分类白名单"
    )
    risk_level_allowlist: Optional[List[str]] = Field(
        default=None, description="允许采样的风险等级白名单"
    )

    def should_sample(
        self,
        case_id: str,
        category: Optional[str] = None,
        risk_level: Optional[str] = None,
        seed: Optional[int] = None,
    ) -> bool:
        """
        确定性采样判断 pure function
        """
        # 1. 默认关闭或零采样率
        if self.sample_rate <= 0.0:
            return False

        # 2. 分类白名单过滤
        if self.category_allowlist is not None and category is not None:
            if category not in self.category_allowlist:
                return False

        # 3. 风险等级白名单过滤
        if self.risk_level_allowlist is not None and risk_level is not None:
            if risk_level not in self.risk_level_allowlist:
                return False

        # 4. 全量采样
        if self.sample_rate >= 1.0:
            return True

        # 5. 基于 SHA-256 的确定性伪随机哈希
        salt = str(seed) if seed is not None else "0"
        hash_digest = hashlib.sha256(f"{case_id}:{salt}".encode("utf-8")).hexdigest()
        norm_val = int(hash_digest[:8], 16) / 0xFFFFFFFF

        return norm_val < self.sample_rate
