# -*- coding: utf-8 -*-
"""
tests.conftest
全局 pytest 配置与测试运行期数据物理隔离 Fixture
"""

import pytest
from pathlib import Path
from app.core.config import settings
from app.infrastructure.persistence.event_repository import default_event_repository
from app.infrastructure.persistence.bkt_state_repository import default_bkt_state_repository
from app.infrastructure.persistence.path_state_repository import default_path_state_repository


@pytest.fixture(autouse=True)
def isolate_runtime_data(tmp_path, monkeypatch, request):
    """
    将所有运行时数据存储文件重定向至隔离的 tmp_path 临时目录，
    确保单元与集成测试绝不污染生产或种子 data/ 目录。
    """
    # test_config 专门检验 Settings 默认路径映射，不应重定向 settings.RUNTIME_DIR
    if "test_config" in request.node.nodeid:
        return

    temp_runtime = tmp_path / "runtime"
    temp_runtime.mkdir(parents=True, exist_ok=True)

    test_events_file = temp_runtime / "test_learning_events.jsonl"
    test_bkt_states_file = temp_runtime / "test_bkt_states.json"
    test_processed_file = temp_runtime / "test_bkt_processed_events.json"
    test_path_states_file = temp_runtime / "test_learning_path_states.json"

    monkeypatch.setattr(settings, "RUNTIME_DIR", temp_runtime)
    monkeypatch.setattr(settings, "LEARNING_EVENTS_FILE", test_events_file)
    monkeypatch.setattr(settings, "BKT_STATES_FILE", test_bkt_states_file)
    monkeypatch.setattr(settings, "BKT_PROCESSED_EVENTS_FILE", test_processed_file)
    monkeypatch.setattr(settings, "LEARNING_PATH_STATES_FILE", test_path_states_file)

    # 重定向仓储单例的默认路径
    monkeypatch.setattr(default_event_repository, "file_path", test_events_file)
    monkeypatch.setattr(default_bkt_state_repository, "states_file", test_bkt_states_file)
    monkeypatch.setattr(default_bkt_state_repository, "processed_file", test_processed_file)
    monkeypatch.setattr(default_path_state_repository, "states_file", test_path_states_file)

    # 兼容历史 facade 模块的全局常量
    import event_service
    import bkt_state_service
    import path_state_service

    monkeypatch.setattr(event_service, "DEFAULT_EVENTS_FILE", test_events_file)
    monkeypatch.setattr(bkt_state_service, "DEFAULT_STATES_FILE", test_bkt_states_file)
    monkeypatch.setattr(bkt_state_service, "DEFAULT_PROCESSED_FILE", test_processed_file)
    monkeypatch.setattr(path_state_service, "DEFAULT_PATH_STATES_FILE", test_path_states_file)
    monkeypatch.setattr(path_state_service, "DATA_DIR", temp_runtime)
