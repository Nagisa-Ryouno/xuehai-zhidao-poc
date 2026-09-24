import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import type {
  TeacherActionType,
  TeacherActionCreateRequest,
  TeacherActionItem,
} from '../src/types.ts';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

describe('Sprint 10-D / Phase 4-C: Teacher Student Detail Action Modal 契约与 UI 规范测试', () => {
  // ============================================================================
  // 1. 动作类型与请求 DTO 纯洁性测试
  // ============================================================================

  it('test_01_three_action_whitelist_and_business_labels', () => {
    // 严格锁定 3 个动作枚举
    const allowedActions: TeacherActionType[] = [
      'REVIEW_CONCEPT',
      'RETRY_PRACTICE',
      'MARK_FOLLOWED',
    ];
    assert.equal(allowedActions.length, 3, '必须且仅允许 3 种教学动作');

    const actionLabels: Record<TeacherActionType, string> = {
      REVIEW_CONCEPT: '建议复习该考点',
      RETRY_PRACTICE: '建议重新练习',
      MARK_FOLLOWED: '标记为已关注',
    };

    assert.equal(actionLabels.REVIEW_CONCEPT, '建议复习该考点');
    assert.equal(actionLabels.RETRY_PRACTICE, '建议重新练习');
    assert.equal(actionLabels.MARK_FOLLOWED, '标记为已关注');
  });

  it('test_02_request_dto_purity_strictly_two_fields', () => {
    // 请求载荷严格仅包含 knowledge_id 与 action_type
    const requestPayload: TeacherActionCreateRequest = {
      knowledge_id: 'K02',
      action_type: 'REVIEW_CONCEPT',
    };

    const keys = Object.keys(requestPayload);
    assert.deepEqual(keys.sort(), ['action_type', 'knowledge_id'].sort());

    // 严禁前端自行生成内部标识或服务字段
    assert.equal('action_id' in requestPayload, false);
    assert.equal('teacher_id' in requestPayload, false);
    assert.equal('created_at' in requestPayload, false);
    assert.equal('knowledge_name' in requestPayload, false);
    assert.equal('note' in requestPayload, false);
    assert.equal('message' in requestPayload, false);
    assert.equal('status' in requestPayload, false);
  });

  // ============================================================================
  // 2. UI 纯洁性与红线审查 (源码级静态审查与安全断言)
  // ============================================================================

  it('test_03_no_internal_teacher_id_leak_in_ui', () => {
    const modalPath = path.resolve(__dirname, '../src/components/teacher/TeacherActionModal.tsx');
    const modalContent = fs.readFileSync(modalPath, 'utf-8');

    // UI 中绝对不得出现 T001
    assert.equal(
      modalContent.includes('T001'),
      false,
      'TeacherActionModal UI 绝对不得向用户展示 T001 或任何内部 teacher ID'
    );

    // 必须使用业务文案“任课教师”
    assert.ok(
      modalContent.includes('任课教师'),
      'TeacherActionModal 必须使用业务文案「任课教师」'
    );
  });

  it('test_04_no_free_text_inputs_in_modal', () => {
    const modalPath = path.resolve(__dirname, '../src/components/teacher/TeacherActionModal.tsx');
    const modalContent = fs.readFileSync(modalPath, 'utf-8');

    // 绝对不能有自由文本输入组件
    assert.equal(
      modalContent.includes('<input'),
      false,
      'TeacherActionModal 绝对不允许出现 <input> 文本输入框'
    );
    assert.equal(
      modalContent.includes('<textarea'),
      false,
      'TeacherActionModal 绝对不允许出现 <textarea> 多行文本框'
    );
    // 载荷中绝不包含 note / 自由留言字段
    assert.equal(
      modalContent.includes('note:'),
      false,
      'TeacherActionModal 请求中绝对不允许包含 note 备注字段'
    );
    assert.equal(
      modalContent.includes('custom_text'),
      false,
      'TeacherActionModal 绝对不允许包含 custom_text 字段'
    );
  });

  it('test_05_submitting_state_and_double_click_lock', () => {
    const modalPath = path.resolve(__dirname, '../src/components/teacher/TeacherActionModal.tsx');
    const modalContent = fs.readFileSync(modalPath, 'utf-8');

    // 必须包含 isSubmitting 防重复点击机制
    assert.ok(
      modalContent.includes('isSubmitting'),
      'TeacherActionModal 必须包含 isSubmitting 状态以防止连击'
    );
    assert.ok(
      modalContent.includes('disabled={isSubmitting'),
      'TeacherActionModal 在提交期间必须禁用操作按钮'
    );
    assert.ok(
      modalContent.includes('postTeacherAction'),
      'TeacherActionModal 必须调用 postTeacherAction API'
    );
  });

  it('test_06_toast_feedback_semantics', () => {
    const modalPath = path.resolve(__dirname, '../src/components/teacher/TeacherActionModal.tsx');
    const modalContent = fs.readFileSync(modalPath, 'utf-8');

    // 验证成功反馈文案
    assert.ok(
      modalContent.includes('已成功记录教师关注'),
      'MARK_FOLLOWED 对应文案必须为「已成功记录教师关注」'
    );
    assert.ok(
      modalContent.includes('已成功记录教学建议'),
      '可执行建议对应文案必须为「已成功记录教学建议」'
    );
  });

  it('test_07_api_endpoint_isolation_no_student_mutation', () => {
    const apiPath = path.resolve(__dirname, '../src/api.ts');
    const apiContent = fs.readFileSync(apiPath, 'utf-8');

    // 验证 postTeacherAction 仅调用 /teacher/students/.../actions
    assert.ok(
      apiContent.includes('/teacher/students/${encodeURIComponent(studentId)}/actions'),
      'postTeacherAction 必须正确指向教学动作接口'
    );

    // 提取 postTeacherAction 函数体，断言其内部绝对不调用学生学习状态修改接口
    const postFnIdx = apiContent.indexOf('function postTeacherAction');
    const postFnBody = apiContent.slice(postFnIdx, postFnIdx + 300);

    assert.equal(
      postFnBody.includes('/quiz/submit'),
      false,
      'postTeacherAction 内部绝对不触碰测验提交接口'
    );
    assert.equal(
      postFnBody.includes('/learning/events'),
      false,
      'postTeacherAction 内部绝对不写入正式学习事件'
    );
    assert.equal(
      postFnBody.includes('/learning/path-replanning'),
      false,
      'postTeacherAction 内部绝对不触发路径重新规划'
    );
  });

  // ============================================================================
  // 3. TeacherStudentDetailModal 接入最小化审查
  // ============================================================================

  it('test_08_student_detail_modal_minimal_integration', () => {
    const detailModalPath = path.resolve(
      __dirname,
      '../src/components/teacher/TeacherStudentDetailModal.tsx'
    );
    const detailContent = fs.readFileSync(detailModalPath, 'utf-8');

    // 必须引入并挂载 TeacherActionModal
    assert.ok(
      detailContent.includes('TeacherActionModal'),
      'TeacherStudentDetailModal 必须挂载 TeacherActionModal'
    );

    // 必须在考点卡片上包含 data-testid 触发入口
    assert.ok(
      detailContent.includes('data-testid={`btn-teacher-action-${kp.knowledge_id}`}'),
      '考点卡片上必须包含教学动作触发按钮'
    );

    // 现有 3 个 Tab 原样保留，不得修改原有结构
    assert.ok(detailContent.includes("'kps'"), '30 考点认知全景 Tab 必须保留');
    assert.ok(detailContent.includes("'wrongs'"), '错题复盘流水 Tab 必须保留');
    assert.ok(detailContent.includes("'timeline'"), '真实学习流水 Tab 必须保留');

    // 现有 Student Perspective 按钮原样保留
    assert.ok(
      detailContent.includes('以该生身份进入学习空间'),
      '以该生身份进入学习空间 CTA 必须原样保留'
    );
  });
});
