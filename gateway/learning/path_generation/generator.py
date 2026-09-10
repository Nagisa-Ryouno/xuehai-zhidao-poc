# -*- coding: utf-8 -*-
"""
gateway/learning/path_generation/generator.py
学海智导 (Xuehai Zhidao) - 动态自适应学习路线生成器

核心规范：
1. 严格复用现有 BKT / PathState / Mastery 判定 (MASTERY_THRESHOLD_HIGH = 0.80)；
2. 拓扑硬约束优先于评分打分 (Prerequisite Supremacy)；
3. Top-3 是至多 3 站 (0 <= route_length <= 3)，决不强塞违规节点；
4. 纯确定性 Tie-break 与保序机制；
5. 全流程安全降级保护，绝不向上抛出未捕获异常。
"""

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Union

from app.core.constants import MASTERY_THRESHOLD_HIGH, PathState
from app.infrastructure.persistence.bkt_state_repository import default_bkt_state_repository
from app.infrastructure.persistence.path_state_repository import default_path_state_repository
from app.services.knowledge_graph_service import CHAPTER_COLUMN_MAP, knowledge_graph_service
from app.services.path_replanning_service import (
    get_prerequisites,
    get_successors,
    is_knowledge_mastered,
)
from gateway.learning.diagnostic.engine import get_latest_diagnostic_result
from gateway.learning.path_generation.models import DynamicLearningRoute, RouteStep
from gateway.learning.path_generation.scoring import calculate_node_priority


def _get_chapter_index(chapter_name: str) -> int:
    return CHAPTER_COLUMN_MAP.get(chapter_name, 99)


def identify_target_knowledge_ids(goal: str) -> List[str]:
    """从学生学习目标中提取目标考点 ID 列表"""
    if not goal:
        return ["K08"]
        
    explicit = re.findall(r"K\d{2}", goal.upper())
    valid_explicit = [k for k in explicit if knowledge_graph_service.is_valid_knowledge_id(k)]
    if valid_explicit:
        return valid_explicit
        
    goal_lower = goal.lower()
    targets: List[str] = []
    if any(kw in goal_lower for kw in ["弹性", "税收", "elasticity"]):
        targets.extend(["K08", "K09", "K11"])
    elif any(kw in goal_lower for kw in ["供求", "均衡", "市场", "equilibrium"]):
        targets.extend(["K04", "K06", "K07"])
    elif any(kw in goal_lower for kw in ["导论", "稀缺", "机会成本", "ppf"]):
        targets.extend(["K01", "K02", "K03"])
    else:
        targets.append("K08")
    return targets


def get_target_ancestor_ids(target_ids: List[str]) -> Set[str]:
    """获取所有目标考点的前置依赖祖先集合（包含目标考点自身）"""
    ancestors: Set[str] = set()
    queue = list(target_ids)
    
    while queue:
        curr = queue.pop(0)
        if curr not in ancestors:
            ancestors.add(curr)
            prereqs = get_prerequisites(curr)
            for p in prereqs:
                if p not in ancestors:
                    queue.append(p)
    return ancestors


class DynamicPathGenerator:
    """动态路径规划生成器"""

    def __init__(
        self,
        bkt_repo=default_bkt_state_repository,
        path_repo=default_path_state_repository,
    ):
        self.bkt_repo = bkt_repo
        self.path_repo = path_repo

    def generate_route(
        self,
        student_id: str,
        goal: str,
        states_file: Optional[Union[Path, str]] = None,
        bkt_states_file: Optional[Union[Path, str]] = None,
    ) -> DynamicLearningRoute:
        """
        为学生生成 Top-3 动态自适应学习路线。
        
        遵循 5 大阶段：
        1. 目标分析与相关考点集合提取；
        2. 全图未掌握考点过滤与前置可达性硬约束校验；
        3. 综合多因子打分与确定性 Tie-Break 排序；
        4. 航线逐步装配（至多 3 站，前置必须严格排在后继之前）；
        5. Invariant 校验与安全降级。
        """
        now_iso = datetime.now(timezone.utc).isoformat()
        
        try:
            target_ids = identify_target_knowledge_ids(goal)
            target_ancestors = get_target_ancestor_ids(target_ids)
            
            # 读取诊断结果（若有）
            diagnostic = get_latest_diagnostic_result(student_id)
            diag_weaknesses = set(diagnostic.weaknesses) if diagnostic else set()
            diag_strengths = set(diagnostic.strengths) if diagnostic else set()
            
            # 获取所有知识点 ID 列表
            all_k_ids = knowledge_graph_service.get_all_knowledge_point_ids()
            
            # 记录当前已掌握的知识点集合
            mastered_nodes: Set[str] = set()
            for kid in all_k_ids:
                if is_knowledge_mastered(student_id, kid, bkt_states_file=bkt_states_file):
                    mastered_nodes.add(kid)
                    
            # 模拟学习进程以依次规划第 1 站 (CURRENT)、第 2 站 (NEXT)、第 3 站 (UPCOMING)
            simulated_mastered = set(mastered_nodes)
            selected_steps: List[RouteStep] = []
            roles = ["CURRENT", "NEXT", "UPCOMING"]
            
            for rank_idx in range(1, 4):
                role = roles[rank_idx - 1]
                
                # 候选池：未掌握且未在本次路线中入选的考点
                # 关键硬约束：其所有前置依赖必须在 simulated_mastered 中已满足！
                candidate_ids: List[str] = []
                for kid in all_k_ids:
                    if kid in simulated_mastered:
                        continue
                    if any(step.knowledge_id == kid for step in selected_steps):
                        continue
                        
                    prereqs = get_prerequisites(kid)
                    # 前置绝对霸权：前置必须全部已被模拟掌握
                    if all(p in simulated_mastered for p in prereqs):
                        candidate_ids.append(kid)
                        
                if not candidate_ids:
                    # 没有更多合法可学习的节点了，提前结束路线装配（0 <= route_length <= 3）
                    break
                    
                # 对候选池进行打分
                scored_candidates: List[Tuple[float, Tuple[int, int, str], RouteStep]] = []
                for kid in candidate_ids:
                    kp = knowledge_graph_service.get_knowledge_point(kid)
                    kname = kp.get("knowledge_name", kid)
                    chapter = kp.get("chapter", "未知章节")
                    diff = kp.get("difficulty", 1)
                    prereqs = get_prerequisites(kid)
                    
                    # 真实掌握度
                    bkt_state = self.bkt_repo.get_state(
                        student_id, kid, states_file=bkt_states_file
                    )
                    mastery_val = bkt_state.mastery_probability if bkt_state else 0.20
                    
                    # 路径状态
                    curr_path_state = self.path_repo.get_path_state(
                        student_id, kid, states_file=states_file
                    )
                    
                    # 诊断状态
                    if kid in diag_weaknesses:
                        diag_status = "WEAK"
                    elif kid in diag_strengths:
                        diag_status = "DEVELOPING"
                    else:
                        diag_status = None
                        
                    is_target_anc = kid in target_ancestors
                    is_same_ch = any(
                        knowledge_graph_service.get_knowledge_point(t).get("chapter") == chapter
                        for t in target_ids
                        if knowledge_graph_service.get_knowledge_point(t)
                    )
                    all_prereqs_satisfied = all(p in simulated_mastered for p in prereqs)
                    
                    score, factors, reason_codes, explanation = calculate_node_priority(
                        knowledge_id=kid,
                        mastery=mastery_val,
                        is_target_ancestor_or_self=is_target_anc,
                        is_same_chapter=is_same_ch,
                        all_prereqs_mastered=all_prereqs_satisfied,
                        path_state=curr_path_state.value,
                        diagnostic_status=diag_status,
                    )
                    
                    # 稳定 Tie-Break Key: (-score, chapter_idx, difficulty, knowledge_id)
                    tie_break_key = (
                        _get_chapter_index(chapter),
                        diff,
                        kid,
                    )
                    
                    step = RouteStep(
                        knowledge_id=kid,
                        knowledge_name=kname,
                        chapter=chapter,
                        rank=rank_idx,
                        role=role,
                        score=score,
                        reason_codes=reason_codes,
                        explanation=explanation,
                        mastery=round(mastery_val, 4),
                        path_state=curr_path_state.value,
                        prerequisites=prereqs,
                    )
                    scored_candidates.append((score, tie_break_key, step))
                    
                # 排序：score 降序，tie_break_key 升序
                scored_candidates.sort(key=lambda item: (-item[0], item[1]))
                best_step = scored_candidates[0][2]
                selected_steps.append(best_step)
                
                # 将该节点加入模拟掌握集，以解锁后继节点参与下一站评选
                simulated_mastered.add(best_step.knowledge_id)
                
            return DynamicLearningRoute(
                student_id=student_id,
                goal=goal,
                route_length=len(selected_steps),
                steps=selected_steps,
                is_fallback=False,
                fallback_reason=None,
                generated_at=now_iso,
            )
            
        except Exception as ex:
            # 安全降级逻辑：绝不向上崩溃抛错，回退至当前学生可用的基础路径
            return self._build_safe_fallback_route(
                student_id=student_id,
                goal=goal,
                now_iso=now_iso,
                reason=f"Exception caught during route generation: {str(ex)}",
                states_file=states_file,
                bkt_states_file=bkt_states_file,
            )

    def _build_safe_fallback_route(
        self,
        student_id: str,
        goal: str,
        now_iso: str,
        reason: str,
        states_file: Optional[Union[Path, str]] = None,
        bkt_states_file: Optional[Union[Path, str]] = None,
    ) -> DynamicLearningRoute:
        """从当前可用的 PathState 构建兜底航线"""
        fallback_steps: List[RouteStep] = []
        try:
            all_states = self.path_repo.get_all_path_states(student_id, states_file=states_file)
            # 寻找 IN_PROGRESS 或 AVAILABLE 的节点
            accessible = [
                k for k, state in all_states.items()
                if state in (PathState.IN_PROGRESS, PathState.AVAILABLE)
            ]
            accessible.sort()
            
            roles = ["CURRENT", "NEXT", "UPCOMING"]
            for idx, kid in enumerate(accessible[:3]):
                kp = knowledge_graph_service.get_knowledge_point(kid) or {}
                kname = kp.get("knowledge_name", kid)
                chapter = kp.get("chapter", "基础章节")
                
                bkt_state = self.bkt_repo.get_state(
                    student_id, kid, states_file=bkt_states_file
                )
                m_val = bkt_state.mastery_probability if bkt_state else 0.20
                p_state = all_states.get(kid, PathState.AVAILABLE)
                
                fallback_steps.append(
                    RouteStep(
                        knowledge_id=kid,
                        knowledge_name=kname,
                        chapter=chapter,
                        rank=idx + 1,
                        role=roles[idx],
                        score=0.50,
                        reason_codes=["SAFE_FALLBACK"],
                        explanation="系统自适应安全降级推荐，优先攻坚当前就绪知识点。",
                        mastery=round(m_val, 4),
                        path_state=p_state.value,
                        prerequisites=get_prerequisites(kid),
                    )
                )
        except Exception:
            pass

        return DynamicLearningRoute(
            student_id=student_id,
            goal=goal,
            route_length=len(fallback_steps),
            steps=fallback_steps,
            is_fallback=True,
            fallback_reason=reason,
            generated_at=now_iso,
        )


default_dynamic_path_generator = DynamicPathGenerator()
