# -*- coding: utf-8 -*-
"""AI 伴学真实 Provider 接入与离线降级回归测试。"""

import pytest

from gateway.adapter import (
    ExternalLLMProvider,
    ProviderException,
    get_provider,
    set_provider,
)
from gateway.config import GatewaySettings
from gateway.learning.companion.models import CompanionMode, CompanionStudyRequest
from gateway.learning.companion.service import CompanionService
from gateway.transport import FakeLLMTransport, HttpLLMTransport


@pytest.fixture(autouse=True)
def reset_active_provider():
    set_provider(None)
    yield
    set_provider(None)


@pytest.mark.asyncio
async def test_companion_uses_external_provider_answer_and_preserves_safety():
    """真实 Provider 成功时必须替换离线答案，但仍不得获得学习决策权。"""
    provider = ExternalLLMProvider(
        name="deepseek",
        api_key="test-key-not-real",
        transport=FakeLLMTransport(
            custom_response_payload={
                "answer": "供需变化要分别判断曲线移动方向，再比较新均衡。",
                "referenced_facts": ["当前考点：K01 稀缺性与经济学基本问题"],
                "suggested_explanation": "先识别变化的是需求还是供给。",
                "grounding_status": "grounded",
            }
        ),
    )
    set_provider(provider)

    response = await CompanionService().handle_companion_request(
        CompanionStudyRequest(
            student_id="S001",
            mode=CompanionMode.CONVERSATION,
            knowledge_id="K01",
            message="供需同时变化时怎么分析？",
        )
    )

    assert response.answer == "供需变化要分别判断曲线移动方向，再比较新均衡。"
    assert response.provider == "deepseek"
    assert response.safety.offline_mode is False
    assert response.safety.allow_production_decision is False
    assert response.referenced_facts == ["当前考点：K01 稀缺性与经济学基本问题"]


@pytest.mark.asyncio
async def test_companion_falls_back_to_offline_answer_when_provider_fails():
    """上游异常不得变成学生端 500，必须返回现有离线辅导答案。"""
    set_provider(
        ExternalLLMProvider(
            name="deepseek",
            api_key="test-key-not-real",
            transport=FakeLLMTransport(mode="http_5xx", status_code=502),
        )
    )

    response = await CompanionService().handle_companion_request(
        CompanionStudyRequest(
            student_id="S001",
            mode=CompanionMode.CONCEPT_EXPLAIN,
            knowledge_id="K01",
        )
    )

    assert "稀缺性" in response.answer
    assert response.provider == "offline"
    assert response.safety.offline_mode is True
    assert response.safety.allow_production_decision is False


def test_deepseek_factory_enables_http_transport(monkeypatch):
    """选择 deepseek 且配置完整时，工厂必须装配真实 HTTP 传输。"""
    configured = GatewaySettings(
        provider="deepseek",
        api_key="test-key-not-real",
        base_url="https://api.deepseek.com",
        model="deepseek-chat",
        timeout_ms=30000,
    )
    monkeypatch.setattr("gateway.adapter.gateway_settings", configured)

    provider = get_provider("deepseek")

    assert isinstance(provider, ExternalLLMProvider)
    assert isinstance(provider.transport, HttpLLMTransport)
    assert provider.transport._get_endpoint_url() == "https://api.deepseek.com/chat/completions"


class _OpenAICompatibleResponse:
    status_code = 200

    def json(self):
        return {
            "id": "chatcmpl-test",
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": (
                            '{"answer":"模型回答","referenced_facts":["事实A"],'
                            '"grounding_status":"grounded"}'
                        ),
                    }
                }
            ],
        }


class _OpenAICompatibleClient:
    def post(self, *args, **kwargs):
        return _OpenAICompatibleResponse()


@pytest.mark.asyncio
async def test_external_provider_parses_openai_compatible_chat_completion():
    """DeepSeek 的 choices[].message.content JSON 必须转换为内部结构化响应。"""
    from gateway.models import (
        LearningPromptContext,
        LearningPromptSystemFacts,
        PromptNextAction,
    )

    context = LearningPromptContext(
        user_question="请解释稀缺性",
        system_facts=LearningPromptSystemFacts(
            student_id="S001",
            student_name="张同学",
            major="经济学",
            grade="大二",
            learning_goal="期末复习",
            current_knowledge_id="K01",
            current_knowledge_name="稀缺性",
            current_chapter="导论",
            current_path_state="IN_PROGRESS",
            current_mastery_percent=20.0,
            mastery_target_percent=80.0,
            mastery_gap_percent=60.0,
            is_mastered=False,
            prerequisites_met=True,
            path_priority="高",
            is_path_completed=False,
            next_action=PromptNextAction(
                type="REVIEW_CONCEPT",
                label="复习概念",
                target_knowledge_id="K01",
                reason="当前仍需巩固",
            ),
        ),
    )
    provider = ExternalLLMProvider(
        name="deepseek",
        api_key="test-key-not-real",
        transport=HttpLLMTransport(
            base_url="https://api.deepseek.com",
            api_key="test-key-not-real",
            client=_OpenAICompatibleClient(),
        ),
    )

    result = await provider.generate(context)

    assert result.answer == "模型回答"
    assert result.referenced_facts == ["事实A"]
