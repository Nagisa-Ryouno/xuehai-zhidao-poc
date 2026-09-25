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

    # Sprint 10-B: DeepSeek 官方配置基线
    # 优先采用 Sprint 10-B 专用变量，同时兼容既有 AI_*/LLM_* 配置，
    # 让已部署环境升级后无需重复填写同一把密钥。
    deepseek_enabled: bool = os.getenv(
        "DEEPSEEK_ENABLED",
        "true" if os.getenv("AI_PROVIDER", "").strip().lower() == "deepseek" else "false",
    ).strip().lower() in ("true", "1", "yes")
    deepseek_api_key: Optional[str] = os.getenv(
        "DEEPSEEK_API_KEY",
        os.getenv("AI_API_KEY", os.getenv("LLM_API_KEY", None)),
    )
    deepseek_base_url: str = os.getenv(
        "DEEPSEEK_BASE_URL",
        os.getenv("AI_BASE_URL", "https://api.deepseek.com"),
    ).strip().rstrip("/")
    deepseek_model: str = os.getenv(
        "DEEPSEEK_MODEL",
        os.getenv("AI_MODEL", "deepseek-flash"),
    ).strip()
    deepseek_timeout_seconds: int = int(os.getenv("DEEPSEEK_TIMEOUT_SECONDS", "20"))

    def get_masked_api_key(self) -> str:
        """获取脱敏后的密钥用于日志记录，禁止明文暴露"""
        if not self.api_key:
            return "<UNSET>"
        clean_key = self.api_key.strip()
        if len(clean_key) <= 8:
            return "***"
        return f"{clean_key[:3]}...{clean_key[-4:]}"

    def get_masked_deepseek_api_key(self) -> str:
        """获取脱敏后的 DeepSeek API 密钥，禁止明文暴露"""
        if not self.deepseek_api_key:
            return "<UNSET>"
        clean_key = self.deepseek_api_key.strip()
        if len(clean_key) <= 8:
            return "***"
        return f"{clean_key[:3]}...{clean_key[-4:]}"

    def is_secret_contained(self, content: str) -> bool:
        """安全检验函数：确保给定字符串中不包含真实密钥（若已配置有效密钥）"""
        for secret in [self.api_key, self.deepseek_api_key]:
            if secret and len(secret.strip()) >= 5 and secret.strip() in content:
                return False
        return True


gateway_settings = GatewaySettings()
