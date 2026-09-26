# -*- coding: utf-8 -*-
"""
gateway.config
学海智导 (Xuehai Zhidao) V2 - Phase 3 / Sprint 7-D
服务端安全配置与密钥隔离边界
"""

import os
from dataclasses import dataclass
from typing import Optional


from pathlib import Path

def _load_env_file() -> None:
    try:
        from dotenv import load_dotenv
        _root = Path(__file__).resolve().parent.parent
        _env = _root / ".env"
        if _env.exists():
            load_dotenv(dotenv_path=_env, override=False)
    except Exception:
        pass

_load_env_file()


@dataclass
class GatewaySettings:
    """服务端独立配置对象，绝不向客户端暴露真实密钥"""
    provider: str = "mock"
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    model: str = "mock-companion-v1"
    timeout_ms: int = 5000

    # Sprint 10-B: DeepSeek 官方配置基线
    deepseek_enabled: bool = False
    deepseek_api_key: Optional[str] = None
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-flash"
    deepseek_timeout_seconds: int = 20

    def __init__(
        self,
        provider: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout_ms: Optional[int] = None,
        deepseek_enabled: Optional[bool] = None,
        deepseek_api_key: Optional[str] = None,
        deepseek_base_url: Optional[str] = None,
        deepseek_model: Optional[str] = None,
        deepseek_timeout_seconds: Optional[int] = None,
    ):
        self.api_key = api_key if api_key is not None else os.getenv("AI_API_KEY", os.getenv("LLM_API_KEY", os.getenv("DEEPSEEK_API_KEY", None)))
        self.base_url = base_url if base_url is not None else os.getenv("AI_BASE_URL", None)
        self.model = (model or os.getenv("AI_MODEL", "mock-companion-v1")).strip()
        self.timeout_ms = timeout_ms if timeout_ms is not None else int(os.getenv("AI_GATEWAY_TIMEOUT_MS", "5000"))

        self.deepseek_api_key = (
            deepseek_api_key
            if deepseek_api_key is not None
            else os.getenv("DEEPSEEK_API_KEY", self.api_key)
        )
        self.deepseek_base_url = (
            (deepseek_base_url or os.getenv("DEEPSEEK_BASE_URL", self.base_url or "https://api.deepseek.com"))
            .strip()
            .rstrip("/")
        )
        self.deepseek_model = (
            deepseek_model or os.getenv("DEEPSEEK_MODEL", os.getenv("AI_MODEL", "deepseek-flash"))
        ).strip()
        self.deepseek_timeout_seconds = (
            deepseek_timeout_seconds
            if deepseek_timeout_seconds is not None
            else int(os.getenv("DEEPSEEK_TIMEOUT_SECONDS", "20"))
        )

        if deepseek_enabled is not None:
            self.deepseek_enabled = deepseek_enabled
        else:
            raw_enabled = os.getenv("DEEPSEEK_ENABLED")
            if raw_enabled is not None:
                self.deepseek_enabled = raw_enabled.strip().lower() in ("true", "1", "yes")
            else:
                raw_prov = (provider or os.getenv("AI_PROVIDER", "")).strip().lower()
                self.deepseek_enabled = raw_prov in ("deepseek", "deepseek-flash", "deepseek-v4-pro")

        if provider is not None:
            self.provider = provider.strip().lower()
        else:
            raw_prov = os.getenv("AI_PROVIDER")
            if raw_prov:
                self.provider = raw_prov.strip().lower()
            elif self.deepseek_enabled and self.deepseek_api_key:
                self.provider = "deepseek"
            else:
                self.provider = "mock"

    def reload(self) -> "GatewaySettings":
        """重新从环境读取配置"""
        _load_env_file()
        self.__init__()
        return self

    def get_masked_api_key(self) -> str:
        """获取脱敏后的密钥用于日志记录，禁止明文暴露"""
        key = self.api_key or self.deepseek_api_key
        if not key:
            return "<UNSET>"
        clean_key = key.strip()
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
