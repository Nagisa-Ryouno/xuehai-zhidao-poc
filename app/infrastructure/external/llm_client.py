# -*- coding: utf-8 -*-
"""
llm_client.py
学海智导 (Xuehai Zhidao) V2 外部大模型服务商抽象与调用客户端 (LLM Client)

职责：
1. 环境变量读取与统一配置 (支持 .env)
2. 抽象并支持 OpenAI 规范兼容的模型提供商 (DeepSeek, 通义千问, OpenAI, Mock 等)
3. 完善的异常拦截 (超时、网络异常、非 200 响应、无效 JSON 拦截)
4. 结构化日志记录 (脱敏，杜绝 API Key 泄漏)
5. 自动降级信号传递 (上层接收 None 时可秒级无缝 fallback 到规则引擎)
"""

import json
import logging
import os
from pathlib import Path
import re
from typing import Any, Dict, Optional

try:
    from dotenv import load_dotenv
    env_path = Path(__file__).resolve().parent.parent.parent.parent / ".env"
    if env_path.exists():
        load_dotenv(dotenv_path=env_path, override=True)
    else:
        load_dotenv(override=True)
except ImportError:
    pass

import requests

logger = logging.getLogger("xuehai.llm")


class LLMClient:
    """LLM 服务商客户端抽象"""

    def __init__(self):
        self.reload_config()

    def reload_config(self):
        """重新读取环境变量配置"""
        self.provider = os.getenv("LLM_PROVIDER", "deepseek").strip().lower()
        self.api_key = os.getenv("LLM_API_KEY", "").strip()
        self.base_url = os.getenv("LLM_BASE_URL", "https://api.deepseek.com").strip()
        self.model = os.getenv("LLM_MODEL", "deepseek-chat").strip()
        try:
            self.timeout = int(os.getenv("LLM_TIMEOUT", "30"))
        except ValueError:
            self.timeout = 30

    def is_available(self) -> bool:
        """
        判断 LLM 服务当前是否具备调用条件
        1. provider 为 mock 时可用
        2. provider 为 none/rule/disabled 时不可用
        3. 其他提供商必须配置非空的真实 API Key
        """
        if self.provider == "mock":
            return True

        if self.provider in ("none", "rule", "disabled", ""):
            return False

        if not self.api_key or self.api_key in ("your_api_key_here", "sk-xxx"):
            return False

        return True

    def get_provider_name(self) -> str:
        """获取当前提供商标识"""
        return self.provider

    def _get_chat_endpoint(self) -> str:
        """拼装标准的 Chat Completions 接口地址"""
        url = self.base_url.rstrip("/")
        if url.endswith("/chat/completions"):
            return url
        if url.endswith("/v1"):
            return f"{url}/chat/completions"
        return f"{url}/chat/completions"

    def _clean_json_text(self, text: str) -> str:
        """清洗大模型可能附带的 Markdown 代码块或前后杂质"""
        text = text.strip()
        pattern = r"```(?:json)?\s*([\s\S]*?)\s*```"
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return text

    def generate(
        self,
        system_prompt: str,
        user_message: str,
        context: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """
        向 LLM 请求结构化学习指导
        成功返回解析后的字典；失败返回 None (触发上层自动降级)
        """
        if not self.is_available():
            return None

        # -------------------------------------------------------------
        # Mock 模式：用于免 Key 演示、快速单元测试与离线评测
        # -------------------------------------------------------------
        if self.provider == "mock":
            return self._generate_mock_response(user_message, context)

        # -------------------------------------------------------------
        # 真实网络请求模式 (基于 OpenAI 兼容协议)
        # -------------------------------------------------------------
        endpoint = self._get_chat_endpoint()
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        user_content = (
            f"【学生真实学情数据上下文】:\n{json.dumps(context, ensure_ascii=False, indent=2)}\n\n"
            f"【学生提问】:\n{user_message}\n\n"
            f"请严格依据上下文数据，以合法 JSON 格式输出回答。"
        )

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            "temperature": 0.3,
            "response_format": {"type": "json_object"},
        }

        try:
            response = requests.post(
                endpoint,
                headers=headers,
                json=payload,
                timeout=self.timeout,
            )

            if response.status_code != 200:
                print(f"[Assistant] fallback=http_error status={response.status_code}")
                return None

            data = response.json()
            choices = data.get("choices", [])
            if not choices:
                print("[Assistant] fallback=empty_choices")
                return None

            raw_content = choices[0].get("message", {}).get("content", "")
            cleaned_content = self._clean_json_text(raw_content)

            parsed = json.loads(cleaned_content)
            if not isinstance(parsed, dict):
                print("[Assistant] fallback=invalid_response_type")
                return None

            return parsed

        except requests.exceptions.Timeout:
            print(f"[Assistant] fallback=timeout (exceeded {self.timeout}s)")
            return None
        except requests.exceptions.RequestException as e:
            print(f"[Assistant] fallback=network_error ({e.__class__.__name__})")
            return None
        except json.JSONDecodeError:
            print("[Assistant] fallback=json_decode_error")
            return None
        except Exception as e:
            print(f"[Assistant] fallback=unexpected_error ({e.__class__.__name__})")
            return None

    def _generate_mock_response(
        self,
        user_message: str,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Mock 模式智能响应生成器
        以大模型亲切、细致的教学口吻包装真实上下文数据，用于无需配置真实 Key 时的完整联调
        """
        student = context.get("student", {})
        student_name = student.get("name", "同学")
        profile = context.get("profile", {})
        avg_acc = profile.get("average_accuracy", 0)
        path = context.get("learning_path", [])
        daily = context.get("daily_plan", {})
        weaks = context.get("weak_knowledge_points", [])

        # 检查是否为 S004 特殊情况
        if len(path) == 0:
            return {
                "answer": (
                    f"{student_name}你好！作为你的专属 AI 导师，我仔细复盘了你的学习档案。"
                    f"令人惊喜的是，你目前的微观经济学平均正确率已经达到 **{avg_acc:.2f}%**，"
                    f"各核心概念掌握非常均衡，**当前并没有检测到任何明显的低正确率薄弱点**！\n\n"
                    f"因此系统未为你安排基础概念的逐级补差路径，推荐策略为【**综合能力提升**】。\n"
                    f"结合你当前平均答题耗时约 {profile.get('answer_time_seconds', 168):.0f} 秒的特点，"
                    f"我建议你将学习重心从基础识记转向【**限时综合推导与解题速度提效**】。"
                ),
                "related_knowledge_points": [],
                "suggested_actions": [
                    "1. 开启限时模拟冲刺：针对中高难度计算大题进行 90 秒限时突破",
                    "2. 演练供求与弹性联动大题：强化消费者均衡与税收归宿交叉推导",
                    "3. 挑战更高难度拓展题：逐步探索完全垄断与博弈论高阶考点",
                ],
            }

        # 检查知识点提及
        mentioned = None
        for step in path:
            k_name = step.get("knowledge_name", "")
            k_id = step.get("knowledge_id", "")
            if (k_name and k_name in user_message) or (k_id and k_id.lower() in user_message.lower()):
                mentioned = step
                break
        if not mentioned:
            for wp in weaks:
                k_name = wp.get("knowledge_name", "")
                k_id = wp.get("knowledge_id", "")
                if (k_name and k_name in user_message) or (k_id and k_id.lower() in user_message.lower()):
                    mentioned = {
                        "knowledge_id": k_id,
                        "knowledge_name": k_name,
                        "accuracy": wp.get("accuracy"),
                        "current_accuracy": wp.get("accuracy"),
                        "priority": "高" if (wp.get("accuracy") or 0) < 60 else "中",
                        "reason": f"当前正确率仅 {wp.get('accuracy')}%, 属于明确薄弱点",
                        "chapter": wp.get("chapter", "相关章节"),
                        "learning_goal": "优先修复知识薄弱点",
                        "source": "薄弱知识点",
                    }
                    break

        if mentioned:
            k_name = mentioned.get("knowledge_name", "")
            k_id = mentioned.get("knowledge_id", "")
            acc = mentioned.get("accuracy", mentioned.get("current_accuracy"))
            acc_str = f"{acc:.1f}%" if acc is not None else "尚无充足记录"
            return {
                "answer": (
                    f"关于你关心的【**{k_name}**】（编号：{k_id}）：\n\n"
                    f"1. **学情现状透视**：你在该模块的实测答题正确率为 **{acc_str}**，优先级标记为【**{mentioned.get('priority', '高')}**】；\n"
                    f"2. **关键成因诊断**：{mentioned.get('reason', '该知识点在整体学科网络中占据枢纽地位')}；\n"
                    f"3. **导师教学建议**：本阶段的核心目标是【{mentioned.get('learning_goal', '修复知识薄弱点')}】。"
                    f"把这个节点彻底攻克后，下游多个强依赖考点的掌握度将同步获得明显跃升！"
                ),
                "related_knowledge_points": [
                    {
                        "knowledge_id": k_id,
                        "knowledge_name": k_name,
                        "accuracy": acc,
                        "priority": mentioned.get("priority", "高"),
                        "reason": mentioned.get("reason", ""),
                        "chapter": mentioned.get("chapter", ""),
                        "learning_goal": mentioned.get("learning_goal", ""),
                        "source": mentioned.get("source", "薄弱知识点"),
                    }
                ],
                "suggested_actions": [
                    f"1. 精读《{mentioned.get('chapter', '对应章节')}》关于【{k_name}】的核心公式与图形推导",
                    f"2. 限时完成 5~8 道针对性自测题，检验核心考点理解程度",
                    "3. 纠正错题并记录错因，再平稳推进下一阶段知识模块",
                ],
            }

        if any(kw in user_message for kw in ["接下来", "下一步", "顺序", "先学", "学什么", "路径"]):
            first_three = path[:3]
            steps_text = "\n".join([
                f"- **Stage {s.get('stage', idx+1)}**：【**{s.get('knowledge_name', '')}**】(当前正确率 {s.get('current_accuracy', s.get('accuracy', 0)):.1f}% · 优先级 {s.get('priority', '中')})\n  - 依据：{s.get('reason', '')}"
                for idx, s in enumerate(first_three)
            ])
            return {
                "answer": (
                    f"{student_name}，我结合微观经济学拓扑图谱与你的作答短板，为你量身规划了最优时序：\n\n"
                    f"{steps_text}\n\n"
                    f"这个顺序严格遵守了“先补前置基石，再破复杂综合”的认知规律，能帮你以最短时间实现提分突破。"
                ),
                "related_knowledge_points": [
                    {
                        "knowledge_id": s.get("knowledge_id", ""),
                        "knowledge_name": s.get("knowledge_name", ""),
                        "accuracy": s.get("current_accuracy", s.get("accuracy")),
                        "priority": s.get("priority", "中"),
                        "reason": s.get("reason", ""),
                    }
                    for s in first_three
                ],
                "suggested_actions": [
                    f"1. 立即聚焦 Stage {first_three[0].get('stage', 1)}：【{first_three[0].get('knowledge_name', '')}】的专项复习",
                    f"2. 攻克学习目标：{first_three[0].get('learning_goal', '巩固薄弱点')}",
                    f"3. 随后稳步衔接 Stage {first_three[1].get('stage', 2)}：【{first_three[1].get('knowledge_name', '')}】"
                    if len(first_three) > 1
                    else "3. 检验阶段成果并更新学情画像",
                ],
            }

        if any(kw in user_message for kw in ["今天", "安排", "任务", "计划"]):
            mins = daily.get("duration_minutes", 30)
            qs = daily.get("question_count", 8)
            focus = daily.get("focus", "基础知识理解与巩固")
            first_s = path[0] if path else None
            return {
                "answer": (
                    f"{student_name}，基于你的学习负荷与今日复习窗口，AI 导师为你定制的今日任务清单如下：\n\n"
                    f"- **建议专注投入**：**{mins} 分钟**（建议采用番茄钟单次专注完成）\n"
                    f"- **精选题量目标**：**{qs} 道精选练习题**\n"
                    f"- **今日突破重心**：【**{focus}**】\n"
                    f"- **核心主攻节点**：【**{first_s['knowledge_name'] if first_s else '综合提升'}**】\n\n"
                    f"保持节奏、重质不重量，完成后系统将实时刷新你的学情雷达！"
                ),
                "related_knowledge_points": [
                    {
                        "knowledge_id": first_s.get("knowledge_id", ""),
                        "knowledge_name": first_s.get("knowledge_name", ""),
                        "accuracy": first_s.get("current_accuracy", first_s.get("accuracy")),
                        "priority": first_s.get("priority", "中"),
                        "reason": first_s.get("reason", ""),
                    }
                ]
                if first_s
                else [],
                "suggested_actions": [
                    f"1. 专注投入 {mins} 分钟，吃透今日突破重心【{focus}】",
                    f"2. 认真完成 {qs} 道配套自测题，重点标注不确定的选项",
                    "3. 查看错因归纳，完成学情数据打卡",
                ],
            }

        # 默认学情总结
        return {
            "answer": (
                f"{student_name}，根据最新学情数据沉淀，你的近期总体平均正确率为 **{avg_acc:.2f}%**，"
                f"处于【**{profile.get('mastery_level', '中等')}**】掌握水平。\n\n"
                f"系统当前识别出 **{len(weaks)} 个薄弱知识点**，核心诊断提示：{context.get('diagnosis', {}).get('description', '建议结合知识依赖链进行精准补强。')}\n"
                f"你可以向我询问“我接下来应该学什么？”获取动态时序，或输入具体知识点名称由我为你拆解攻坚策略！"
            ),
            "related_knowledge_points": [
                {
                    "knowledge_id": wp["knowledge_id"],
                    "knowledge_name": wp["knowledge_name"],
                    "accuracy": wp["accuracy"],
                    "priority": "高" if (wp.get("accuracy") or 0) < 60 else "中",
                    "reason": f"答题正确率 {wp.get('accuracy')}%, 亟需攻克",
                }
                for wp in weaks[:3]
            ],
            "suggested_actions": [
                "1. 查看个性化学习路径中的推荐时序",
                "2. 针对高风险知识点进行逐一重点击破",
                "3. 保持良好的日常学习活跃度",
            ],
        }


# 全局默认单例
llm_client = LLMClient()
LLMService = LLMClient

__all__ = [
    "LLMClient",
    "LLMService",
    "llm_client",
]
