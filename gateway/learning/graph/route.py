# -*- coding: utf-8 -*-
"""
gateway/learning/graph/route.py
学海智导 (Xuehai Zhidao) - 动态学习路线图谱叠加与高亮服务

职责：
1. 计算航线节点高亮标签 (CURRENT, NEXT, UPCOMING) 与徽章信息；
2. 计算航线流动高亮边集合 (highlighted_edges)；
3. 将动态学习航线无缝叠加至学生知识图谱拓扑中，确保原有数据结构 100% 完好。
"""

from typing import Any, Dict, List, Optional

from app.services.knowledge_graph_service import knowledge_graph_service
from gateway.learning.path_generation.models import DynamicLearningRoute


ROLE_LABELS = {
    "CURRENT": "当前焦点",
    "NEXT": "紧接学习",
    "UPCOMING": "进阶延伸",
}


def get_route_graph_overlay(
    student_id: str,
    route: DynamicLearningRoute,
) -> Dict[str, Any]:
    """
    基于给定的动态路线，计算知识图谱高亮叠加层数据。
    """
    node_roles: Dict[str, str] = {}
    node_ranks: Dict[str, int] = {}
    node_badges: Dict[str, str] = {}
    node_explanations: Dict[str, str] = {}
    
    for step in route.steps:
        kid = step.knowledge_id
        node_roles[kid] = step.role
        node_ranks[kid] = step.rank
        role_desc = ROLE_LABELS.get(step.role, step.role)
        node_badges[kid] = f"第{step.rank}站·{role_desc}"
        node_explanations[kid] = step.explanation
        
    highlighted_edges: List[Dict[str, Any]] = []
    # 航线时序流动边：连接第 1 站 -> 第 2 站 -> 第 3 站
    for i in range(len(route.steps) - 1):
        s1 = route.steps[i]
        s2 = route.steps[i + 1]
        edge_id = f"route-flow-{s1.knowledge_id}-{s2.knowledge_id}"
        highlighted_edges.append({
            "id": edge_id,
            "source": s1.knowledge_id,
            "target": s2.knowledge_id,
            "type": "routeEdge",
            "animated": True,
            "data": {
                "source_role": s1.role,
                "target_role": s2.role,
                "source_name": s1.knowledge_name,
                "target_name": s2.knowledge_name,
                "label": f"第{s1.rank}站 → 第{s2.rank}站",
                "is_active_route": True,
            },
        })

    return {
        "student_id": student_id,
        "goal": route.goal,
        "route_length": route.route_length,
        "node_roles": node_roles,
        "node_ranks": node_ranks,
        "node_badges": node_badges,
        "node_explanations": node_explanations,
        "highlighted_edges": highlighted_edges,
        "is_fallback": route.is_fallback,
        "fallback_reason": route.fallback_reason,
    }


def apply_route_overlay_to_graph(
    base_graph: Dict[str, Any],
    route: DynamicLearningRoute,
) -> Dict[str, Any]:
    """
    将动态路线叠加到学生基础知识图谱数据上，返回带有航线高亮信息的图谱字典。
    保留原有 nodes/edges 的全部字段，不引入破坏性变更。
    """
    overlay = get_route_graph_overlay(route.student_id, route)
    node_roles = overlay["node_roles"]
    node_ranks = overlay["node_ranks"]
    node_badges = overlay["node_badges"]
    node_explanations = overlay["node_explanations"]

    # 深度拷贝或复用并更新节点
    new_nodes = []
    for node in base_graph.get("nodes", []):
        node_copy = dict(node)
        data_copy = dict(node.get("data", {}))
        kid = node.get("id")
        
        if kid in node_roles:
            data_copy["is_on_route"] = True
            data_copy["route_role"] = node_roles[kid]
            data_copy["route_rank"] = node_ranks[kid]
            data_copy["route_badge"] = node_badges[kid]
            data_copy["route_explanation"] = node_explanations[kid]
        else:
            data_copy["is_on_route"] = False
            data_copy["route_role"] = None
            data_copy["route_rank"] = None
            data_copy["route_badge"] = None
            data_copy["route_explanation"] = None
            
        node_copy["data"] = data_copy
        new_nodes.append(node_copy)

    # 组合原有边与高亮航线边
    new_edges = list(base_graph.get("edges", []))
    for r_edge in overlay["highlighted_edges"]:
        # 避免 ID 重复
        if not any(e.get("id") == r_edge["id"] for e in new_edges):
            new_edges.append(r_edge)

    return {
        "metadata": base_graph.get("metadata", {}),
        "student": base_graph.get("student", {}),
        "nodes": new_nodes,
        "edges": new_edges,
        "dynamic_route": route.model_dump(),
        "route_overlay": overlay,
    }
