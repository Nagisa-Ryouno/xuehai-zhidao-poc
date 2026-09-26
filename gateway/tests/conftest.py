# -*- coding: utf-8 -*-
"""
gateway.tests.conftest
======================
Pytest test fixtures ensuring zero test data pollution.
Automatically restores data/ runtime files to their pre-test state upon session completion.
"""

import pytest
from pathlib import Path
from app.core.config import settings
from gateway.adapter import MockGatewayProvider, set_provider
from gateway.config import GatewaySettings, gateway_settings


@pytest.fixture(autouse=True)
def isolate_external_ai_provider(monkeypatch):
    """每项测试默认使用确定性 Provider，严禁开发机 .env 触发真实计费请求。"""
    offline_settings = GatewaySettings(
        provider="mock",
        api_key=None,
        base_url=None,
        model="mock-companion-v1",
        deepseek_enabled=False,
        deepseek_api_key=None,
    )
    monkeypatch.setattr("gateway.adapter.gateway_settings", offline_settings)
    monkeypatch.setattr(
        "gateway.ai.recommendation.generator.gateway_settings",
        offline_settings,
    )
    monkeypatch.setattr(
        "gateway.ai.recommendation.service.gateway_settings",
        offline_settings,
    )
    # 部分历史测试通过 ``from gateway.config import gateway_settings`` 持有
    # 单例引用；同时临时冻结该只读 dataclass 的测试视图，避免本机 .env
    # 改变“默认离线”契约断言。
    original_deepseek = (
        gateway_settings.deepseek_enabled,
        gateway_settings.deepseek_api_key,
        gateway_settings.deepseek_model,
    )
    object.__setattr__(gateway_settings, "deepseek_enabled", False)
    object.__setattr__(gateway_settings, "deepseek_api_key", None)
    object.__setattr__(gateway_settings, "deepseek_model", "deepseek-flash")
    set_provider(MockGatewayProvider())
    yield
    set_provider(None)
    object.__setattr__(gateway_settings, "deepseek_enabled", original_deepseek[0])
    object.__setattr__(gateway_settings, "deepseek_api_key", original_deepseek[1])
    object.__setattr__(gateway_settings, "deepseek_model", original_deepseek[2])


@pytest.fixture(scope="session", autouse=True)
def preserve_data_directory_isolation():
    """
    Session-wide fixture ensuring no test run permanently mutates data/ files.
    Backs up files that may be written to by integration tests and restores them in teardown.
    """
    data_dir = settings.DATA_DIR
    tracked_files = [
        "companion_events.jsonl",
        "learning_sessions.json",
        "resource_effectiveness_events.jsonl",
        "resource_events.jsonl",
        "learning_events.jsonl",
        "bkt_states.json",
        "bkt_processed_events.json",
        "learning_path_states.json",
    ]
    backups = {}
    for filename in tracked_files:
        f = data_dir / filename
        if f.exists():
            backups[filename] = f.read_bytes()
        else:
            backups[filename] = None

    yield

    # Restore exact state
    for filename, content in backups.items():
        f = data_dir / filename
        if content is None:
            if f.exists():
                f.unlink()
        else:
            f.write_bytes(content)
