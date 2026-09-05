# -*- coding: utf-8 -*-
"""
tests/test_path_replanning_core.py
学海智导 V2 - Path Replanning Decision Core 契约层与规范化序列化器测试
严格覆盖 17 项契约与序列化确定性要求。
"""
import hashlib
import json
import unittest
import uuid
from decimal import Decimal
from pydantic import ValidationError

from path_state_service import PathState
from path_replanning_service import (
    PathAction,
    ReplanningReasonCode,
    LEGAL_DECISION_PAIRS,
    validate_decision_pair,
    format_canonical_mastery,
    CanonicalBusinessPayload,
    AuditMetadata,
    DecisionAuditEnvelope,
)


class TestPathReplanningCore(unittest.TestCase):
    """Path Replanning 契约与规范化序列化核心测试套件"""

    def _create_standard_payload(
        self,
        student_id: str = "stu_001",
        knowledge_id: str = "K08",
        before_mastery: str = "0.2000",
        after_mastery: str = "0.8119",
        before_path_state: PathState = PathState.AVAILABLE,
        after_path_state: PathState = PathState.COMPLETED,
        action: PathAction = PathAction.UNLOCK_DOWNSTREAM,
        reason_code: ReplanningReasonCode = ReplanningReasonCode.MASTERY_THRESHOLD_REACHED,
        affected_nodes=None,
    ) -> CanonicalBusinessPayload:
        if affected_nodes is None:
            affected_nodes = ["K09", "K10"]
        return CanonicalBusinessPayload(
            student_id=student_id,
            knowledge_id=knowledge_id,
            before_mastery=before_mastery,
            after_mastery=after_mastery,
            before_path_state=before_path_state,
            after_path_state=after_path_state,
            action=action,
            reason_code=reason_code,
            affected_nodes=affected_nodes,
        )

    # 1. 4 位定点字符串测试 (0.2 -> "0.2000", 0.45661 -> "0.4566", 0.81180 -> "0.8118")
    def test_01_format_canonical_mastery_four_decimals(self):
        self.assertEqual(format_canonical_mastery(0.2), "0.2000")
        self.assertEqual(format_canonical_mastery(0.45661), "0.4566")
        self.assertEqual(format_canonical_mastery(0.81180), "0.8118")
        self.assertEqual(format_canonical_mastery(0.0), "0.0000")
        self.assertEqual(format_canonical_mastery(1.0), "1.0000")

    # 2. HALF_UP 边界行为 (0.81185 -> "0.8119", 0.12725 -> "0.1273")
    def test_02_format_canonical_mastery_half_up_boundary(self):
        self.assertEqual(format_canonical_mastery(0.81185), "0.8119")
        self.assertEqual(format_canonical_mastery(0.12725), "0.1273")
        self.assertEqual(format_canonical_mastery(0.81184), "0.8118")
        self.assertEqual(format_canonical_mastery(0.12724), "0.1272")

    # 3. before_mastery / after_mastery 类型断言 (为 str 非 float)
    def test_03_mastery_type_assertion(self):
        payload = self._create_standard_payload()
        self.assertIsInstance(payload.before_mastery, str)
        self.assertNotIsInstance(payload.before_mastery, float)
        self.assertIsInstance(payload.after_mastery, str)
        self.assertNotIsInstance(payload.after_mastery, float)

        # 传入裸 float 必须被拒绝
        with self.assertRaises((ValidationError, TypeError, ValueError)):
            CanonicalBusinessPayload(
                student_id="stu_001",
                knowledge_id="K08",
                before_mastery=0.2,  # 裸 float
                after_mastery="0.8119",
                before_path_state=PathState.AVAILABLE,
                after_path_state=PathState.COMPLETED,
                action=PathAction.UNLOCK_DOWNSTREAM,
                reason_code=ReplanningReasonCode.MASTERY_THRESHOLD_REACHED,
            )

    # 4. Canonical Payload 字段白名单检验 (不包含 decision_id, timestamp, trace_id, duration_ms)
    def test_04_canonical_payload_fields_whitelist(self):
        field_keys = set(CanonicalBusinessPayload.model_fields.keys())
        forbidden_fields = {"decision_id", "timestamp", "trace_id", "duration_ms"}
        self.assertTrue(
            forbidden_fields.isdisjoint(field_keys),
            f"CanonicalBusinessPayload 不得包含审计或时序字段: {forbidden_fields & field_keys}",
        )

        # 尝试传入额外非法字段应被拒
        with self.assertRaises(ValidationError):
            CanonicalBusinessPayload(
                student_id="stu_001",
                knowledge_id="K08",
                before_mastery="0.2000",
                after_mastery="0.8119",
                before_path_state=PathState.AVAILABLE,
                after_path_state=PathState.COMPLETED,
                action=PathAction.UNLOCK_DOWNSTREAM,
                reason_code=ReplanningReasonCode.MASTERY_THRESHOLD_REACHED,
                decision_id="illegal_decision_id",
            )

    # 5. Audit Metadata 独立模型存在与独立实例化
    def test_05_audit_metadata_independent_model(self):
        meta = AuditMetadata()
        self.assertIsInstance(meta, AuditMetadata)
        # decision_id 格式为 UUID
        uuid_obj = uuid.UUID(meta.decision_id)
        self.assertEqual(str(uuid_obj), meta.decision_id)
        # timestamp 必须为 ISO 格式且以 Z 结尾
        self.assertTrue(meta.timestamp.endswith("Z"))
        self.assertIsNone(meta.trace_id)

        # 支持显式传参
        custom_meta = AuditMetadata(
            decision_id="custom-id-001",
            timestamp="2026-09-05T12:00:00Z",
            trace_id="trace-xyz",
        )
        self.assertEqual(custom_meta.decision_id, "custom-id-001")
        self.assertEqual(custom_meta.timestamp, "2026-09-05T12:00:00Z")
        self.assertEqual(custom_meta.trace_id, "trace-xyz")

    # 6. 相同业务 Payload 多次序列化一致
    def test_06_identical_payload_serialization_consistency(self):
        payload = self._create_standard_payload()
        first_json = payload.to_canonical_json()
        for _ in range(50):
            self.assertEqual(payload.to_canonical_json(), first_json)

    # 7. 修改 decision_id / timestamp 绝不影响 Canonical Payload 序列化结果
    def test_07_audit_metadata_isolation_from_canonical_json(self):
        payload = self._create_standard_payload()
        meta1 = AuditMetadata(decision_id="id-1", timestamp="2026-09-01T00:00:00Z", trace_id="tr-1")
        meta2 = AuditMetadata(decision_id="id-2", timestamp="2026-09-05T23:59:59Z", trace_id="tr-2")

        env1 = DecisionAuditEnvelope(audit_metadata=meta1, canonical_payload=payload)
        env2 = DecisionAuditEnvelope(audit_metadata=meta2, canonical_payload=payload)

        json1 = env1.canonical_payload.to_canonical_json()
        json2 = env2.canonical_payload.to_canonical_json()
        self.assertEqual(json1, json2)

    # 8. sort_keys=True 键顺序检验
    def test_08_sort_keys_true_ordering(self):
        payload = self._create_standard_payload()
        canonical_json = payload.to_canonical_json()
        raw_keys = list(json.loads(canonical_json, object_pairs_hook=lambda pairs: [k for k, _ in pairs]))
        sorted_keys = sorted(raw_keys)
        self.assertEqual(raw_keys, sorted_keys)
        self.assertEqual(
            raw_keys,
            [
                "action",
                "affected_nodes",
                "after_mastery",
                "after_path_state",
                "before_mastery",
                "before_path_state",
                "knowledge_id",
                "reason_code",
                "rule_version",
                "student_id",
            ],
        )

    # 9. separators=(',', ':') 紧凑无空格检验
    def test_09_separators_compact_no_whitespace(self):
        payload = self._create_standard_payload()
        canonical_json = payload.to_canonical_json()
        self.assertNotIn(": ", canonical_json)
        self.assertNotIn(", ", canonical_json)
        self.assertNotIn("\n", canonical_json)
        self.assertNotIn("\r", canonical_json)
        self.assertIn(":", canonical_json)
        self.assertIn(",", canonical_json)

    # 10. ensure_ascii=False 检验
    def test_10_ensure_ascii_false_native_utf8(self):
        payload = self._create_standard_payload(
            student_id="学生_测试号01",
            knowledge_id="知识点_K08",
        )
        canonical_json = payload.to_canonical_json()
        self.assertIn("学生_测试号01", canonical_json)
        self.assertIn("知识点_K08", canonical_json)
        self.assertNotIn(r"\u", canonical_json)

    # 11. affected_nodes 乱序传入后自动 ASCII 升序排列
    def test_11_affected_nodes_ascii_sort_and_dedup(self):
        payload = self._create_standard_payload(
            affected_nodes=["K11", "K03", "K09", "K03", "K01"]
        )
        canonical_json = payload.to_canonical_json()
        parsed = json.loads(canonical_json)
        self.assertEqual(parsed["affected_nodes"], ["K01", "K03", "K09", "K11"])

    # 12. affected_nodes 为空时输出 []
    def test_12_affected_nodes_empty_list(self):
        payload = self._create_standard_payload(affected_nodes=[])
        canonical_json = payload.to_canonical_json()
        parsed = json.loads(canonical_json)
        self.assertEqual(parsed["affected_nodes"], [])
        self.assertIn('"affected_nodes":[]', canonical_json)

    # 13. rule_version 固定为 "v1.0"
    def test_13_rule_version_fixed_v1_0(self):
        payload = self._create_standard_payload()
        self.assertEqual(payload.rule_version, "v1.0")

        # 尝试设置非 v1.0 应被拒绝
        with self.assertRaises((ValidationError, ValueError)):
            CanonicalBusinessPayload(
                rule_version="v2.0",
                student_id="stu_001",
                knowledge_id="K08",
                before_mastery="0.2000",
                after_mastery="0.8119",
                before_path_state=PathState.AVAILABLE,
                after_path_state=PathState.COMPLETED,
                action=PathAction.UNLOCK_DOWNSTREAM,
                reason_code=ReplanningReasonCode.MASTERY_THRESHOLD_REACHED,
            )

    # 14. 5 组合法配对 validate_decision_pair 成功
    def test_14_five_legal_decision_pairs_success(self):
        self.assertEqual(len(LEGAL_DECISION_PAIRS), 5)

        expected_pairs = {
            (PathAction.UNLOCK_DOWNSTREAM, ReplanningReasonCode.MASTERY_THRESHOLD_REACHED),
            (PathAction.RETAIN, ReplanningReasonCode.MASTERY_THRESHOLD_REACHED),
            (PathAction.RETAIN, ReplanningReasonCode.MASTERY_STATE_UNCHANGED),
            (PathAction.RETAIN, ReplanningReasonCode.PREREQUISITE_NOT_READY),
            (PathAction.DEMOTE_TO_REVIEW, ReplanningReasonCode.REVIEW_REQUIRED_DEMOTION),
        }
        self.assertEqual(LEGAL_DECISION_PAIRS, expected_pairs)

        # 逐一验证合法配对均成功不报错
        for action, reason in LEGAL_DECISION_PAIRS:
            validate_decision_pair(action, reason)
            # 同样验证在 CanonicalBusinessPayload 中合法
            payload = self._create_standard_payload(action=action, reason_code=reason)
            self.assertEqual(payload.action, action)
            self.assertEqual(payload.reason_code, reason)

    # 15. 非法配对 validate_decision_pair 抛出 ValueError
    def test_15_illegal_decision_pairs_raise_value_error(self):
        illegal_pairs = [
            (PathAction.UNLOCK_DOWNSTREAM, ReplanningReasonCode.MASTERY_STATE_UNCHANGED),
            (PathAction.UNLOCK_DOWNSTREAM, ReplanningReasonCode.PREREQUISITE_NOT_READY),
            (PathAction.UNLOCK_DOWNSTREAM, ReplanningReasonCode.REVIEW_REQUIRED_DEMOTION),
            (PathAction.DEMOTE_TO_REVIEW, ReplanningReasonCode.MASTERY_THRESHOLD_REACHED),
            (PathAction.DEMOTE_TO_REVIEW, ReplanningReasonCode.MASTERY_STATE_UNCHANGED),
            (PathAction.DEMOTE_TO_REVIEW, ReplanningReasonCode.PREREQUISITE_NOT_READY),
        ]

        for action, reason in illegal_pairs:
            with self.assertRaises(ValueError):
                validate_decision_pair(action, reason)

            # 在 CanonicalBusinessPayload 中传入非法配对也应被校验拦截
            with self.assertRaises((ValidationError, ValueError)):
                self._create_standard_payload(action=action, reason_code=reason)

    # 16. Canonical JSON 多次序列化字节级一致
    def test_16_canonical_json_byte_level_determinism(self):
        payload1 = self._create_standard_payload()
        payload2 = self._create_standard_payload()
        bytes1 = payload1.to_canonical_json().encode("utf-8")
        bytes2 = payload2.to_canonical_json().encode("utf-8")
        self.assertEqual(bytes1, bytes2)
        self.assertEqual(len(bytes1), len(bytes2))

    # 17. SHA-256 哈希多次运行一致
    def test_17_sha256_hash_consistency(self):
        payload = self._create_standard_payload()
        hash1 = hashlib.sha256(payload.to_canonical_json().encode("utf-8")).hexdigest()
        for _ in range(50):
            payload_new = self._create_standard_payload()
            hash_new = hashlib.sha256(payload_new.to_canonical_json().encode("utf-8")).hexdigest()
            self.assertEqual(hash1, hash_new)
        self.assertEqual(len(hash1), 64)


if __name__ == "__main__":
    unittest.main()
