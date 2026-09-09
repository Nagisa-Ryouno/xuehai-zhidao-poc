# -*- coding: utf-8 -*-
"""
gateway.config
学海智导 (Xuehai Zhidao) V2 - Phase 3 / Sprint 7-D
服务端安全配置与密钥隔离边界
"""

import os
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class GatewaySettings:
    """服务端独立配置对象，绝不向客户端暴露真实密钥"""
    provider: str = os.getenv("AI_PROVIDER", "mock").strip().lower()
    api_key: Optional[str] = os.getenv("AI_API_KEY", os.getenv("LLM_API_KEY", None))
    base_url: Optional[str] = os.getenv("AI_BASE_URL", None)
    model: str = os.getenv("AI_MODEL", "mock-companion-v1").strip()
    timeout_ms: int = int(os.getenv("AI_GATEWAY_TIMEOUT_MS", "5000"))

    def get_masked_api_key(self) -> str:
        """获取脱敏后的密钥用于日志记录，禁止明文暴露"""
        if not self.api_key:
            return "<UNSET>"
        clean_key = self.api_key.strip()
        if len(clean_key) <= 8:
            return "***"
        return f"{clean_key[:3]}...{clean_key[-4:]}"

    def is_secret_contained(self, content: str) -> bool:
        """安全检验函数：确保给定字符串中不包含真实密钥（若已配置有效密钥）"""
        if not self.api_key or len(self.api_key.strip()) < 5:
            return True
        return self.api_key.strip() not in content


gateway_settings = GatewaySettings()
