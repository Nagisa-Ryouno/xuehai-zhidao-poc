# -*- coding: utf-8 -*-
"""
verify_assistant_v2.py
验证 LLM 驱动升级后的 AI 学习助手 (8 个核心测试 Case)
"""

import os
import sys
import json
import assistant_service
from llm_service import llm_service

print("=" * 70)
print("学海智导 · AI 学习助手 V2 全量测试套件")
print("=" * 70)

# -------------------------------------------------------------
# 测试 1: Mock 模式下执行 6 个典型问答 (Case 1 ~ Case 6)
# -------------------------------------------------------------
print("\n>>> 阶段一：启用 Mock LLM Provider 测试业务场景 (Case 1 ~ Case 6)")
os.environ["LLM_PROVIDER"] = "mock"
llm_service.reload_config()

test_cases = [
    ("Case 1 (S001 成绩学情)", "S001", "我的成绩怎么样？", ["80.5", "中等"]),
    ("Case 2 (S001 知识点原因)", "S001", "为什么推荐我学习需求价格弹性？", ["42", "K08", "需求价格弹性"]),
    ("Case 3 (S003 稀缺性原因)", "S003", "我为什么要先学习稀缺性？", ["45", "K01", "稀缺性"]),
    ("Case 4 (S003 今日任务)", "S003", "帮我安排今天的学习任务", ["30", "8"]),
    ("Case 5 (S004 综合拔高)", "S004", "我接下来应该学习什么？", ["89.42", "综合能力提升"]),
    ("Case 6 (S005 掌握度查询)", "S005", "消费者最优选择我掌握得怎么样？", ["58", "K15", "消费者最优选择"]),
]

for title, stu, q, expected_keywords in test_cases:
    print(f"\n--- {title} ---")
    print(f"学生: {stu}, 提问: {q}")
    res = assistant_service.generate_assistant_response(stu, q)
    answer = res["answer"]
    kps = res["related_knowledge_points"]
    actions = res["suggested_actions"]

    print("回答预览:", answer[:100].replace("\n", " ") + "...")
    print(f"关联知识点: {len(kps)} 个, 下一步行动: {len(actions)} 条")

    # 验证关键事实无偏差
    for kw in expected_keywords:
        assert kw in answer or any(kw in str(k) for k in kps), f"未能检索到关键事实: {kw}"
    print("[PASS] 事实数据与上下文完全吻合!")

# -------------------------------------------------------------
# 测试 2: Case 7 - 无 API Key / Provider=none 时自动 Fallback 到规则引擎
# -------------------------------------------------------------
print("\n>>> 阶段二：Case 7 - 模拟未配置 API Key 自动降级")
os.environ["LLM_PROVIDER"] = "deepseek"
os.environ["LLM_API_KEY"] = ""  # 清空 Key
llm_service.reload_config()

assert not llm_service.is_available(), "LLM 在无 Key 状态下应不可用"
res_fb = assistant_service.generate_assistant_response("S001", "我的成绩怎么样？")
assert "80.5" in res_fb["answer"], "降级回复中必须包含正确率事实"
print("[PASS] Case 7 验证通过：无 Key 状态平滑降级，返回准确规则回答!")

# -------------------------------------------------------------
# 测试 3: Case 8 - 模拟 LLM 返回畸变/非合法 JSON 时自动 Fallback
# -------------------------------------------------------------
print("\n>>> 阶段三：Case 8 - 模拟 LLM 格式非法/校验失败时自动降级")
# 临时劫持 llm_service.generate 返回畸变数据
original_gen = llm_service.generate

try:
    # 模拟 1: 返回空字符串
    llm_service.is_available = lambda: True
    llm_service.generate = lambda *args, **kwargs: None
    res_err1 = assistant_service.generate_assistant_response("S001", "我的成绩怎么样？")
    assert "80.5" in res_err1["answer"]
    print("[PASS] 模拟请求失败/超时 -> 成功触发降级!")

    # 模拟 2: 返回缺少 answer 的非法 JSON
    llm_service.generate = lambda *args, **kwargs: {"wrong_key": "some value"}
    res_err2 = assistant_service.generate_assistant_response("S001", "我的成绩怎么样？")
    assert "80.5" in res_err2["answer"]
    print("[PASS] 模拟缺少 answer 字段 -> 成功触发降级!")

    # 模拟 3: 包含伪造的知识点 (如 K999) -> 校验清洗或降级
    llm_service.generate = lambda *args, **kwargs: {
        "answer": "这是一条正常的回答",
        "related_knowledge_points": [{"knowledge_id": "K999_FAKE", "knowledge_name": "虚构经济学", "accuracy": 99}],
        "suggested_actions": ["行动1"]
    }
    res_err3 = assistant_service.generate_assistant_response("S001", "为什么推荐我学习需求价格弹性？")
    # 验证是否过滤了虚构知识点
    for kp in res_err3.get("related_knowledge_points", []):
        assert kp["knowledge_id"] != "K999_FAKE", "严禁输出虚构知识点编号"
    print("[PASS] 模拟注入虚构知识点 -> 校验层成功拦截/清洗!")

finally:
    llm_service.generate = original_gen
    llm_service.reload_config()

print("\n" + "=" * 70)
print("全部 8 项核心测试用例验证 100% 通过！")
print("=" * 70)
