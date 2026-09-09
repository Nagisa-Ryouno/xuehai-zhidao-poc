# -*- coding: utf-8 -*-
"""
gateway.evaluation.shadow.fixtures.mock_transport
学海智导 (Xuehai Zhidao) V2 - Phase 3 / Sprint 7-D
Stage G4: Controlled Mock Real Judge Transport Harness (完全离线仿真传输层)

设计原则：
1. 100% 离线：绝对不发起外部真实网络调用，纯本地可控场景仿真
2. 故障注入矩阵：支持 SUCCESS, TIMEOUT, 429, 500, 401, 403, INVALID_JSON, SCHEMA_ERROR, HIGH_LATENCY
3. 支持动态场景序列：支持重试与熔断器状态跃迁精确检验
"""

import asyncio
import json
from typing import Any, Dict, List, Optional
from gateway.transport import LLMTransport


class MockRealJudgeTransport(LLMTransport):
    """
    离线受控 RealLLMJudge 仿真网络传输层
    """

    def __init__(
        self,
        mode: str = "SUCCESS",
        scenario_sequence: Optional[List[str]] = None,
        custom_response: Optional[Dict[str, Any]] = None,
        simulated_latency_ms: float = 0.0,
    ):
        self.mode = mode
        self.scenario_sequence = list(scenario_sequence) if scenario_sequence else []
        self.custom_response = custom_response
        self.simulated_latency_ms = simulated_latency_ms
        self.call_count: int = 0
        self.sent_payloads: List[Dict[str, Any]] = []

    async def send_payload(
        self,
        request_payload: Dict[str, Any],
        timeout_ms: int,
    ) -> Dict[str, Any]:
        self.call_count += 1
        self.sent_payloads.append(request_payload)

        # 确定当前调用场景
        if self.scenario_sequence:
            current_mode = self.scenario_sequence.pop(0)
        else:
            current_mode = self.mode

        # 模拟超时
        if current_mode == "TIMEOUT":
            raise TimeoutError(f"Simulated LLM Transport timeout after {timeout_ms}ms")

        # 模拟 HTTP 429 速率限制
        if current_mode == "HTTP_429":
            raise RuntimeError("HTTP 429 Too Many Requests: Rate limit exceeded")

        # 模拟 HTTP 500 服务端内部崩溃
        if current_mode == "HTTP_500":
            raise RuntimeError("HTTP 500 Internal Server Error: Remote model crashed")

        # 模拟 HTTP 401 未授权
        if current_mode == "HTTP_401":
            raise RuntimeError("HTTP 401 Unauthorized: Invalid API key")

        # 模拟 HTTP 403 权限不足
        if current_mode == "HTTP_403":
            raise RuntimeError("HTTP 403 Forbidden: Access denied")

        # 模拟畸形 JSON
        if current_mode == "INVALID_JSON":
            return {
                "choices": [
                    {
                        "message": {
                            "content": "```json\n{ unclosed_broken_json: true, \n"
                        }
                    }
                ]
            }

        # 模拟 Schema 字段缺失或评分越界
        if current_mode == "SCHEMA_ERROR":
            return {
                "choices": [
                    {
                        "message": {
                            "content": json.dumps({
                                "pedagogical_score": 1.5,  # 越界
                                "overall_score": 1.5,
                            })
                        }
                    }
                ]
            }

        # 默认正常成功返回 (支持自定义定制)
        default_content = {
            "pedagogical_score": 0.88,
            "contextual_score": 0.85,
            "explanation_score": 0.90,
            "actionability_score": 0.86,
            "overall_score": 0.87,
            "confidence": 0.92,
            "valid": True,
            "rationale_summary": "高质量教学回答，符合认知规律并包含明确行动指引。",
            "violations": [],
        }

        if self.custom_response is not None:
            content_dict = self.custom_response
        else:
            content_dict = default_content

        return {
            "id": f"chatcmpl-mock-{self.call_count}",
            "object": "chat.completion",
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": json.dumps(content_dict, ensure_ascii=False),
                    },
                    "finish_reason": "stop",
                }
            ],
            "usage": {"total_tokens": 120},
        }
