# -*- coding: utf-8 -*-
"""
verify_knowledge_graph.py
全量自动化回归测试脚本：验证「AI 知识图谱」与智能学习路径联动
覆盖 Case 1 ~ Case 5
"""

import requests
import json

BASE_URL = "http://127.0.0.1:8000"

print("=" * 70)
print("学海智导 · AI 知识图谱工作台全量自动化回归测试")
print("=" * 70)

# -------------------------------------------------------------
# Case 1: S001 (张同学) 局部弹性薄弱与 3 阶段推荐路径
# -------------------------------------------------------------
print("\n>>> [Case 1] 验证 S001 (张同学) 知识网络与局部薄弱联动")
r1 = requests.get(f"{BASE_URL}/api/students/S001/knowledge-graph")
assert r1.status_code == 200, f"S001 请求失败: {r1.status_code}"
d1 = r1.json()

assert d1["stats"]["total_nodes"] == 30, "知识点总数必须为 30"
assert d1["stats"]["weak_count"] == 3, f"S001 薄弱点数应为 3, 实际: {d1['stats']['weak_count']}"
assert d1["stats"]["recommended_count"] == 3, "S001 推荐路径阶段应为 3"

# 检查 K08 (需求价格弹性)
k08 = next((n["data"] for n in d1["nodes"] if n["id"] == "K08"), None)
assert k08 is not None, "未找到 K08 节点"
assert k08["accuracy"] == 42.0, f"K08 正确率应为 42.0%, 实际: {k08['accuracy']}"
assert k08["is_weak"] is True, "K08 必须标记为薄弱点"
assert k08["is_recommended"] is True, "K08 必须标记在推荐路径中"
assert k08["path_stage"] == 1, "K08 必须为 Stage 1"
print("[PASS] Case 1: S001 基础指标、K08 节点数据及 3 阶段路径 100% 吻合!")

# -------------------------------------------------------------
# Case 2: S003 (王同学) 12 个薄弱点与 K01 前置枢纽高亮
# -------------------------------------------------------------
print("\n>>> [Case 2] 验证 S003 (王同学) 多薄弱点与 K01 前置基石")
r2 = requests.get(f"{BASE_URL}/api/students/S003/knowledge-graph")
assert r2.status_code == 200, f"S003 请求失败: {r2.status_code}"
d2 = r2.json()

assert d2["stats"]["weak_count"] == 12, f"S003 薄弱点应为 12, 实际: {d2['stats']['weak_count']}"
k01 = next((n["data"] for n in d2["nodes"] if n["id"] == "K01"), None)
assert k01 is not None, "未找到 K01"
assert k01["accuracy"] == 45.0, f"K01 正确率应为 45.0%, 实际: {k01['accuracy']}"
assert k01["is_weak"] is True, "K01 应为薄弱点"
assert k01["is_prerequisite"] is True, "K01 必须标识为前置基石"
assert k01["path_stage"] == 1, "K01 应为 Stage 1 起点"
assert "K01" in d2["ai_insight"], "AI 洞察应指出 K01 的枢纽地位"
print("[PASS] Case 2: S003 12 个薄弱点识别、K01 前置枢纽及 AI 洞察验证通过!")

# -------------------------------------------------------------
# Case 3: S004 (赵同学) 高分场景保护 (89.42%, 0 薄弱点, 0 路径)
# -------------------------------------------------------------
print("\n>>> [Case 3] 验证 S004 (赵同学) 高分场景保护")
r3 = requests.get(f"{BASE_URL}/api/students/S004/knowledge-graph")
assert r3.status_code == 200, f"S004 请求失败: {r3.status_code}"
d3 = r3.json()

assert d3["stats"]["average_accuracy"] == 89.42, "S004 平均正确率应为 89.42"
assert d3["stats"]["weak_count"] == 0, f"S004 薄弱点必须为 0, 实际: {d3['stats']['weak_count']}"
assert d3["stats"]["recommended_count"] == 0, "S004 推荐路径应为 0"

# 严格核查：绝不能有任何节点被标记为 is_weak
weak_nodes = [n for n in d3["nodes"] if n["data"]["is_weak"]]
assert len(weak_nodes) == 0, f"S004 严禁出现薄弱节点, 发现: {len(weak_nodes)}"
assert "🎉" in d3["ai_insight"] and "综合能力提升" in d3["ai_insight"], "AI 洞察必须为综合能力提升"
print("[PASS] Case 3: S004 0 薄弱点保护、高分综合能力提升验证 100% 成功!")

# -------------------------------------------------------------
# Case 4: S005 (刘同学) 18 个未学知识点 accuracy=None 保护
# -------------------------------------------------------------
print("\n>>> [Case 4] 验证 S005 (刘同学) 空值保护与未学节点规范")
r4 = requests.get(f"{BASE_URL}/api/students/S005/knowledge-graph")
assert r4.status_code == 200, f"S005 请求失败: {r4.status_code}"
d4 = r4.json()

unstudied = [n["data"] for n in d4["nodes"] if n["data"]["accuracy"] is None]
assert len(unstudied) == 18, f"S005 未学知识点应为 18 个, 实际: {len(unstudied)}"
for item in unstudied:
    assert item["status"] == "UNSTUDIED", f"未学知识点状态必须为 UNSTUDIED, 实际: {item['status']}"
    assert item["accuracy"] is None, "未学知识点 accuracy 必须严格为 None"

# 检查已学唯一薄弱点 K15 (消费者最优选择)
k15 = next((n["data"] for n in d4["nodes"] if n["id"] == "K15"), None)
assert k15 is not None, "未找到 K15"
assert k15["accuracy"] == 58.0, f"K15 正确率应为 58.0%, 实际: {k15['accuracy']}"
assert k15["is_weak"] is True, "K15 必须标记为薄弱点"
print("[PASS] Case 4: S005 18 个未学节点 None 严格保护、K15 薄弱点定位通过!")

# -------------------------------------------------------------
# Case 5: 全量 5 名学生切换与数据隔离测试
# -------------------------------------------------------------
print("\n>>> [Case 5] 验证 5 名学生切换独立性与无交叉污染")
students = ["S001", "S002", "S003", "S004", "S005"]
results = {}

for s in students:
    res = requests.get(f"{BASE_URL}/api/students/{s}/knowledge-graph").json()
    results[s] = {
        "name": res["student_name"],
        "weak": res["stats"]["weak_count"],
        "acc": res["stats"]["average_accuracy"],
        "rec": res["stats"]["recommended_count"],
    }

print("5 名学生独立学情图谱摘要：")
for sid, info in results.items():
    print(f"  [{sid}] {info['name']}: 平均正确率={info['acc']}%, 薄弱点={info['weak']}个, 推荐={info['rec']}阶段")

# 验证各学生数据独立
assert results["S003"]["weak"] > results["S001"]["weak"], "S003 薄弱点数量应显著多于 S001"
assert results["S004"]["weak"] == 0, "S004 薄弱点为 0"
assert results["S004"]["acc"] > 85, "S004 正确率 > 85"
print("[PASS] Case 5: 5 名学生切换完全独立，无任何状态污染!")

# -------------------------------------------------------------
# 联动测试: 测试知识点点击 -> "问问 AI" 链路调用
# -------------------------------------------------------------
print("\n>>> 联动测试：模拟图谱节点详情点击【问问 AI】调用现有 Assistant 接口")
chat_res = requests.post(
    f"{BASE_URL}/api/students/S003/assistant",
    json={"message": "为什么推荐我先学习【稀缺性与经济学基本问题】？"}
)
assert chat_res.status_code == 200, f"问问 AI 调用失败: {chat_res.status_code}"
ans_data = chat_res.json()
assert "稀缺性" in ans_data["answer"] or "K01" in ans_data["answer"], "AI 解答中必须包含所选知识点"
print("[PASS] 联动测试：知识图谱节点 -> AI 学习助手深度问答调用成功!")

print("\n" + "=" * 70)
print("全部 5 项回归测试与 AI 联动测试 100% 通过！")
print("=" * 70)
