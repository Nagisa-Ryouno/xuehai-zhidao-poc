# -*- coding: utf-8 -*-
"""
gateway.teacher_actions
=======================
学海智导 (Xuehai Zhidao) — Sprint 10-D Phase 4: Teacher Action Loop
教师轻量教学动作核心领域模型与持久化仓储层 (Intervention Lite Repository)

设计规范与架构红线：
1. 极简白名单动作 (Intervention Lite)：
   严格限定为三种轻量动作：REVIEW_CONCEPT, RETRY_PRACTICE, MARK_FOLLOWED。
2. 教学动作 != 学习事实：
   教师动作仅作为管理/关注流水与学生端辅助建议，绝对不修改 BKT 概率，
   不修改 PathState 节点状态，不写入正式 learning_events.jsonl。
3. 纯确定性、零 AI 介入：无任何大模型调用或非确定性启发逻辑。
4. 物理隔离持久化：
   生产数据写入 data/teacher_actions.jsonl（Append-Only JSONL）。
   支持 file_path 依赖注入，自动化测试严格隔离至 tmp_path。
5. 服务端 5 秒防重复提交保护 (Duplicate Submission Protection)：
   同一 (student_id, knowledge_id, action_type) 在 5.0 秒内重复提交，
   直接返回已有记录，避免并发或连击产生多余写入。
6. 学生端 7 天 Freshness Window 与条数截断（纯读取规则）：
   学生端建议仅读取 7 天内的可执行动作 (REVIEW_CONCEPT / RETRY_PRACTICE)，
   MARK_FOLLOWED 仅作教师关注记录，不流向学生，也不覆盖/注销此前建议；
   同一考点取最新一条，按 created_at 倒序，最多返回 3 条。
   底层模型不增设 status / expires_at / consumed 等任何复杂状态机。
7. 考点名称解耦存储：
   底层仅持久化 knowledge_id，读取时动态匹配 CONCEPT_CARDS 单一事实来源。
"""

import json
import threading
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Union
from pydantic import BaseModel, Field, ConfigDict

from app.core.config import settings
from gateway.content.concept_cards import CONCEPT_CARDS

# 严格白名单动作枚举
TeacherActionType = Literal["REVIEW_CONCEPT", "RETRY_PRACTICE", "MARK_FOLLOWED"]
VALID_ACTION_TYPES = frozenset({"REVIEW_CONCEPT", "RETRY_PRACTICE", "MARK_FOLLOWED"})
ACTIONABLE_ACTION_TYPES = frozenset({"REVIEW_CONCEPT", "RETRY_PRACTICE"})

# 生产环境默认持久化文件路径
DEFAULT_TEACHER_ACTIONS_FILE = settings.DATA_DIR / "teacher_actions.jsonl"


# ==========================================
# 1. 领域模型定义 (Domain Models)
# ==========================================

class TeacherActionCreateRequest(BaseModel):
    """教师发起轻量教学动作请求载荷 (POST)"""
    model_config = ConfigDict(extra="ignore")

    knowledge_id: str = Field(..., description="目标考点编号，如 K02")
    action_type: TeacherActionType = Field(..., description="严格白名单动作类型")


class TeacherActionRecord(BaseModel):
    """
    底层最小持久化实体 (Append-Only JSONL 单行记录)
    绝对不持久化 knowledge_name (保持单一事实来源)
    绝对不持久化 note / message (杜绝自由文本)
    绝对不包含 status / expires_at / consumed 等状态机字段
    """
    action_id: str = Field(..., description="服务端生成的动作唯一标识，如 act-tea-abc123def456")
    teacher_id: str = Field(default="T001", description="服务端固定的任课教师上下文内部标识，当前固定为 T001")
    student_id: str = Field(..., description="目标学生编号，如 S001")
    knowledge_id: str = Field(..., description="目标考点编号，如 K02")
    action_type: TeacherActionType = Field(..., description="严格白名单动作类型")
    created_at: str = Field(..., description="服务端权威 ISO 8601 UTC 时间戳")


class TeacherActionItem(BaseModel):
    """教师端全量历史流水条目 (读取模型，含动态匹配的 knowledge_name)"""
    action_id: str = Field(..., description="动作唯一标识")
    teacher_id: str = Field(default="T001", description="任课教师内部标识")
    student_id: str = Field(..., description="学生编号")
    knowledge_id: str = Field(..., description="考点编号")
    knowledge_name: str = Field(..., description="运行时动态匹配的考点名称")
    action_type: TeacherActionType = Field(..., description="动作类型")
    created_at: str = Field(..., description="记录时间戳")


class TeacherActionHistoryResponse(BaseModel):
    """教师端学生动作全量历史响应模型 (永久保留全量流水)"""
    student_id: str = Field(..., description="学生编号")
    total_count: int = Field(..., description="历史动作总数")
    actions: List[TeacherActionItem] = Field(default_factory=list, description="全量历史动作列表 (created_at DESC)")


class StudentRecommendationItem(BaseModel):
    """学生端轻量学习建议条目 (读取模型，仅限 actionable 类型，最多 3 条)"""
    action_id: str = Field(..., description="动作唯一标识")
    knowledge_id: str = Field(..., description="考点编号")
    knowledge_name: str = Field(..., description="运行时动态匹配的考点名称")
    action_type: Literal["REVIEW_CONCEPT", "RETRY_PRACTICE"] = Field(..., description="学生可执行的建议类型")
    created_at: str = Field(..., description="建议发起时间戳")


class StudentRecommendationsResponse(BaseModel):
    """学生端辅助学习建议响应模型"""
    student_id: str = Field(..., description="学生编号")
    total_count: int = Field(..., description="有效建议数量 (最多 3 条)")
    recommendations: List[StudentRecommendationItem] = Field(
        default_factory=list, description="按考点最新聚合去重、最近7天、最多3条的建议列表"
    )


# ==========================================
# 2. 持久化仓储实现 (Repository)
# ==========================================

def _parse_iso_datetime(iso_str: str) -> datetime:
    """解析 ISO 8601 时间戳为带时区的 UTC datetime"""
    try:
        dt = datetime.fromisoformat(iso_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return datetime.min.replace(tzinfo=timezone.utc)


class TeacherActionRepository:
    """
    教师轻量动作持久化仓储
    - 线程安全 (threading.RLock)
    - 追加写 JSONL (Append-Only)
    - 路径依赖注入 (file_path injection for test isolation)
    - 服务端 5 秒防重复提交保护
    - 学生端 7 天 freshness window 与条数上限纯读取过滤
    """

    def __init__(self, file_path: Optional[Union[Path, str]] = None):
        if file_path is not None:
            self.file_path: Path = Path(file_path)
        else:
            self.file_path: Path = DEFAULT_TEACHER_ACTIONS_FILE
        self._lock = threading.RLock()

    def record_action(
        self,
        student_id: str,
        knowledge_id: str,
        action_type: str,
        teacher_id: str = "T001",
        now: Optional[datetime] = None,
    ) -> TeacherActionRecord:
        """
        记录一条教师教学动作
        1. 严格校验 knowledge_id 与 action_type 合法性；
        2. 5 秒内同一 (student_id, knowledge_id, action_type) 重复提交保护：
           若命中 5 秒时间窗，直接返回已有记录，不重复写入；
        3. 生成服务端权威唯一 action_id 与 created_at 并以 JSONL 形式原子追加。
        """
        if knowledge_id not in CONCEPT_CARDS:
            raise ValueError(f"找不到指定考点：{knowledge_id}")

        if action_type not in VALID_ACTION_TYPES:
            raise ValueError(f"非法的教学动作类型：{action_type}")

        current_time = now or datetime.now(timezone.utc)
        if current_time.tzinfo is None:
            current_time = current_time.replace(tzinfo=timezone.utc)

        with self._lock:
            # 检查 5 秒防重复提交保护
            existing_records = self._read_records_unlocked()
            matching_recent = [
                r for r in existing_records
                if r.student_id == student_id
                and r.knowledge_id == knowledge_id
                and r.action_type == action_type
            ]
            if matching_recent:
                # 检查最新一条的时间差
                latest_match = matching_recent[-1]
                latest_dt = _parse_iso_datetime(latest_match.created_at)
                diff_seconds = abs((current_time - latest_dt).total_seconds())
                if diff_seconds < 5.0:
                    # 命中 5 秒防重时间窗，直接返回已有记录
                    return latest_match

            # 生成新记录
            action_id = f"act-tea-{uuid.uuid4().hex[:12]}"
            created_at_str = current_time.isoformat()
            record = TeacherActionRecord(
                action_id=action_id,
                teacher_id=teacher_id or "T001",
                student_id=student_id,
                knowledge_id=knowledge_id,
                action_type=action_type,  # type: ignore[arg-type]
                created_at=created_at_str,
            )

            # 确保父目录存在并追加写入
            self.file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.file_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(record.model_dump(), ensure_ascii=False) + "\n")

            return record

    def _read_records_unlocked(self) -> List[TeacherActionRecord]:
        """内部读取全量记录 (调用前须持有 self._lock 或供只读方法使用)"""
        if not self.file_path.exists():
            return []

        records: List[TeacherActionRecord] = []
        with open(self.file_path, "r", encoding="utf-8") as f:
            for line in f:
                clean_line = line.strip()
                if not clean_line:
                    continue
                try:
                    data = json.loads(clean_line)
                    records.append(TeacherActionRecord(**data))
                except Exception:
                    continue
        return records

    def get_actions_for_student(self, student_id: str) -> List[TeacherActionRecord]:
        """
        获取指定学生的所有历史教学动作记录
        按 created_at 降序排列 (最新在前)，包含全量流水 (含 MARK_FOLLOWED)
        """
        with self._lock:
            all_records = self._read_records_unlocked()

        student_records = [r for r in all_records if r.student_id == student_id]
        # 按时间倒序排序
        student_records.sort(
            key=lambda r: _parse_iso_datetime(r.created_at),
            reverse=True,
        )
        return student_records

    def get_teacher_action_history(self, student_id: str) -> TeacherActionHistoryResponse:
        """
        教师端全量动作历史只读模型
        - 永久保留全部动作；
        - 动态注入 CONCEPT_CARDS 中的 knowledge_name；
        - 按时间倒序；
        - 不受 7 天时效限制，不受条数上限截断。
        """
        records = self.get_actions_for_student(student_id)
        items: List[TeacherActionItem] = []
        for r in records:
            card = CONCEPT_CARDS.get(r.knowledge_id)
            k_name = card.knowledge_name if card else r.knowledge_id
            items.append(
                TeacherActionItem(
                    action_id=r.action_id,
                    teacher_id=r.teacher_id,
                    student_id=r.student_id,
                    knowledge_id=r.knowledge_id,
                    knowledge_name=k_name,
                    action_type=r.action_type,
                    created_at=r.created_at,
                )
            )
        return TeacherActionHistoryResponse(
            student_id=student_id,
            total_count=len(items),
            actions=items,
        )

    def get_student_recommendations(
        self,
        student_id: str,
        now: Optional[datetime] = None,
        max_items: int = 3,
    ) -> StudentRecommendationsResponse:
        """
        学生端辅助学习建议只读模型 (管道化严格读取规则)
        管道规则：
        1. 仅限最近 7 天内 (created_at >= now - 7 days) 的动作；
        2. 仅限 actionable 动作 (REVIEW_CONCEPT / RETRY_PRACTICE)；
           MARK_FOLLOWED 永远过滤，不流向学生，且不覆盖/注销此前建议；
        3. 同一 knowledge_id 仅保留最新一条建议 (按 created_at DESC 去重)；
        4. 按 created_at 倒序排列；
        5. 严格截断最多 max_items 条 (默认 3 条)；
        6. 运行时动态解析 knowledge_name。
        """
        current_time = now or datetime.now(timezone.utc)
        if current_time.tzinfo is None:
            current_time = current_time.replace(tzinfo=timezone.utc)

        cutoff_time = current_time - timedelta(days=7)

        # 1. 获取按时间倒序的全量学生动作
        records = self.get_actions_for_student(student_id)

        # 2. 过滤 7 天时效与 actionable 动作
        actionable_within_7d: List[TeacherActionRecord] = []
        for r in records:
            r_dt = _parse_iso_datetime(r.created_at)
            # 超过 7 天不进入学生端
            if r_dt < cutoff_time:
                continue
            # 仅消费 REVIEW_CONCEPT 与 RETRY_PRACTICE (MARK_FOLLOWED 永不进入)
            if r.action_type in ACTIONABLE_ACTION_TYPES:
                actionable_within_7d.append(r)

        # 3. 按 knowledge_id 去重 (由于 records 已经倒序排列，首次遇到的即为该考点最新建议)
        seen_knowledge_ids = set()
        deduped: List[TeacherActionRecord] = []
        for r in actionable_within_7d:
            if r.knowledge_id not in seen_knowledge_ids:
                seen_knowledge_ids.add(r.knowledge_id)
                deduped.append(r)

        # 4. 最多截取 max_items 条 (默认 3 条)
        limited = deduped[:max_items]

        # 5. 动态注入 knowledge_name 并包装响应
        recommendations: List[StudentRecommendationItem] = []
        for r in limited:
            card = CONCEPT_CARDS.get(r.knowledge_id)
            k_name = card.knowledge_name if card else r.knowledge_id
            recommendations.append(
                StudentRecommendationItem(
                    action_id=r.action_id,
                    knowledge_id=r.knowledge_id,
                    knowledge_name=k_name,
                    action_type=r.action_type,  # type: ignore[arg-type]
                    created_at=r.created_at,
                )
            )

        return StudentRecommendationsResponse(
            student_id=student_id,
            total_count=len(recommendations),
            recommendations=recommendations,
        )


# 全局默认单例仓储实例
default_teacher_action_repository = TeacherActionRepository()
