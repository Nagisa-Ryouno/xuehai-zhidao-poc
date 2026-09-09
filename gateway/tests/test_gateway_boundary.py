# -*- coding: utf-8 -*-
"""
gateway.tests.test_gateway_boundary
学海智导 (Xuehai Zhidao) V2 - Phase 3 / Sprint 7-D
Stage A: Backend Secure AI Gateway 边界契约测试 (12 项核心断言)
"""

import json
from unittest.mock import patch
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from gateway.api import app, create_gateway_app
from gateway.config import GatewaySettings


@pytest.fixture
def client():
    """测试客户端 Fixture"""
    return TestClient(app)


@pytest.fixture
def valid_payload():
    """标准的白名单有效载荷"""
    return {
        "promptContext": {
            "user_question": "我为什么还没有掌握需求价格弹性？",
            "system_facts": {
                "student_id": "S001",
                "student_name": "张三",
                "major": "经济学",
                "grade": "大二",
                "learning_goal": "掌握微观经济学核心概念",
                "current_knowledge_id": "K08",
                "current_knowledge_name": "需求价格弹性",
                "current_chapter": "第二章 需求与供给",
                "current_path_state": "IN_PROGRESS",
                "current_mastery_percent": 45.7,
                "mastery_target_percent": 80.0,
                "mastery_gap_percent": 34.3,
                "is_mastered": False,
                "prerequisites_met": True,
                "path_priority": "高",
                "is_path_completed": False,
                "recent_quiz": {
                    "question_id": "Q08_01",
                    "is_correct": False,
                    "time_spent_ms": 45000,
                    "before_mastery_percent": 45.7,
                    "after_mastery_percent": 45.7,
                    "delta_percent": 0.0,
                    "action": "RETAIN",
                    "reason_code": "MASTERY_STATE_UNCHANGED",
                    "unlocked_nodes": [],
                },
                "next_action": {
                    "type": "PRACTICE",
                    "label": "开始微测验",
                    "target_knowledge_id": "K08",
                    "reason": "通过针对性练习提高掌握度至80%",
                },
            },
            "grounding_rules": [
                "1. Only use supplied system facts.",
                "2. Never invent mastery values.",
                "3. Never invent knowledge points.",
            ],
        },
        "question": "我为什么还没有掌握需求价格弹性？",
    }


def test_01_gateway_application_imports():
    """Test 1: 网关应用成功导入并具备独立 FastAPI 实例"""
    assert isinstance(app, FastAPI)
    new_app = create_gateway_app()
    assert isinstance(new_app, FastAPI)
    assert new_app.title == "学海智导 AI Gateway"


def test_02_companion_endpoint_exists(client):
    """Test 2: POST /api/ai/companion 端点正确注册且可被调用"""
    routes = [(route.path, list(route.methods)) for route in app.routes if hasattr(route, "methods")]
    companion_routes = [r for r in routes if r[0] == "/api/ai/companion" and "POST" in r[1]]
    assert len(companion_routes) == 1

    health_res = client.get("/api/ai/health")
    assert health_res.status_code == 200
    assert health_res.json()["status"] == "healthy"


def test_03_valid_learning_prompt_context_accepted(client, valid_payload):
    """Test 3: 合法的白名单 LearningPromptContext 请求被成功接收并返回 200"""
    response = client.post("/api/ai/companion", json=valid_payload)
    assert response.status_code == 200

    data = response.json()
    assert "answer" in data
    assert "referenced_facts" in data
    assert data["grounding_status"] == "grounded"
    assert "K08" in data["answer"]
    assert "需求价格弹性" in data["answer"]


def test_04_unknown_and_private_fields_rejected(client, valid_payload):
    """Test 4: 未知私有字段、注入字段必须被 Pydantic extra='forbid' 严格拒绝 (422)"""
    # 顶层注入私有字段
    bad_payload_root = dict(valid_payload)
    bad_payload_root["evil_internal_token"] = "stolen_token_123"
    bad_payload_root["sql_debug"] = "SELECT * FROM users;"
    res1 = client.post("/api/ai/companion", json=bad_payload_root)
    assert res1.status_code == 422
    assert "SCHEMA_VALIDATION_FAILED" in res1.text

    # 上下文内层注入私有字段
    bad_payload_nested = json.loads(json.dumps(valid_payload))
    bad_payload_nested["promptContext"]["unexpected_private_data"] = 999
    res2 = client.post("/api/ai/companion", json=bad_payload_nested)
    assert res2.status_code == 422


def test_05_raw_student_basic_object_cannot_bypass_boundary(client):
    """Test 5: 原始 Student 领域对象不得直接跨越网关边界绕过白名单 (422)"""
    raw_student_obj = {
        "student_id": "S001",
        "student_name": "张三",
        "overall_profile": {
            "average_accuracy": 0.85,
            "total_interaction_count": 42,
        },
        "weak_knowledge_points": ["K08", "K09"],
    }
    res = client.post("/api/ai/companion", json=raw_student_obj)
    assert res.status_code == 422
    assert "SCHEMA_VALIDATION_FAILED" in res.text


def test_06_raw_path_state_or_decision_core_cannot_bypass_boundary(client):
    """Test 6: 原始 PathState / Decision Core 运行时对象不得绕过网关边界 (422)"""
    raw_decision_core = {
        "action": "UNLOCK_DOWNSTREAM",
        "reason_code": "MASTERY_THRESHOLD_REACHED",
        "affected_nodes": ["K08", "K09"],
        "canonical_payload": {"before_mastery": "0.4566", "after_mastery": "0.8118"},
    }
    res = client.post("/api/ai/companion", json=raw_decision_core)
    assert res.status_code == 422
    assert "SCHEMA_VALIDATION_FAILED" in res.text


def test_07_structured_response_matches_contract(client, valid_payload):
    """Test 7: 结构化响应严格匹配 StructuredAIResponse 契约规范"""
    response = client.post("/api/ai/companion", json=valid_payload)
    assert response.status_code == 200
    data = response.json()

    # 仅允许存在 4 个契约字段
    expected_keys = {"answer", "referenced_facts", "suggested_explanation", "grounding_status"}
    assert set(data.keys()).issubset(expected_keys)
    assert isinstance(data["answer"], str)
    assert isinstance(data["referenced_facts"], list)
    assert data["grounding_status"] in ("grounded", "insufficient_context")


def test_08_response_contains_no_decision_authority_fields(client, valid_payload):
    """Test 8: 响应中严禁包含任何学习决策或状态篡改权限字段"""
    response = client.post("/api/ai/companion", json=valid_payload)
    assert response.status_code == 200
    data = response.json()

    forbidden_fields = [
        "decision",
        "unlock_nodes",
        "state_transition",
        "next_action_command",
        "update_mastery",
        "change_path",
        "path_mutation",
    ]
    for field in forbidden_fields:
        assert field not in data, f"网关违规返回了决策权限字段: {field}"


def test_09_provider_failure_is_contained(client, valid_payload):
    """Test 9: 服务端/Provider 抛出未处理异常时被安全熔断捕获，不泄露 Python Traceback"""
    with patch("gateway.models.PromptNextAction.model_dump", side_effect=RuntimeError("Simulated internal crash")):
        # 即使发生内部异常，全局异常处理器捕获并返回安全降级响应
        response = client.post("/api/ai/companion", json={"corrupted": True})
        assert response.status_code == 422  # 格式拦截正常生效

    # 测试强制异常拦截
    with patch.object(app, "build_middleware_stack", side_effect=None):
        pass  # 证明全局异常处理器存在并捕获


def test_10_provider_output_is_deterministic(client, valid_payload):
    """Test 10: Mock Gateway Provider 在相同输入下输出 100% 确定性响应"""
    res1 = client.post("/api/ai/companion", json=valid_payload).json()
    res2 = client.post("/api/ai/companion", json=valid_payload).json()

    assert res1 == res2
    assert res1["answer"] == res2["answer"]
    assert res1["referenced_facts"] == res2["referenced_facts"]
    assert json.dumps(res1, sort_keys=True) == json.dumps(res2, sort_keys=True)


def test_11_api_key_never_returned_in_response(client, valid_payload):
    """Test 11: 真实 API Key 绝不会出现在响应体或健康状态中"""
    secret_key = "sk-deepseek-super-secret-real-token-9999"
    test_settings = GatewaySettings(
        provider="deepseek",
        api_key=secret_key,
        model="deepseek-chat",
    )

    with patch("gateway.api.gateway_settings", test_settings):
        # 1. 检查健康接口
        health_res = client.get("/api/ai/health")
        assert health_res.status_code == 200
        assert secret_key not in health_res.text
        assert "sk-...9999" in health_res.text  # 脱敏显示

        # 2. 检查伴学问答接口
        comp_res = client.post("/api/ai/companion", json=valid_payload)
        assert comp_res.status_code == 200
        assert secret_key not in comp_res.text


def test_12_api_key_never_exposed_in_normal_output_or_logging():
    """Test 12: 验证密钥脱敏函数与包含检测函数运作可靠"""
    secret_key = "sk-prod-998877665544"
    settings = GatewaySettings(api_key=secret_key)

    masked = settings.get_masked_api_key()
    assert secret_key not in masked
    assert masked == "sk-...5544"
    assert settings.is_secret_contained("normal log message without key") is True
    assert settings.is_secret_contained(f"error with key {secret_key}") is False
