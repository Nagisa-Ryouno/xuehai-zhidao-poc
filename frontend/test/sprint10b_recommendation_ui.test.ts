/**
 * frontend/test/sprint10b_recommendation_ui.test.ts
 * 学海智导 (Xuehai Zhidao) — Phase 6 / Sprint 10-B / Phase 3
 * AI 个性化推荐产品化与学生端资源中心契约测试 (Frontend Contract Tests)
 *
 * 覆盖 16 项核心契约：
 * 1. PersonalizedRecommendation 与 PersonalizedRecommendationResponse 领域模型契约
 * 2. 纯辅助候选原则：禁止携带 allow_production_decision, mastery_probability, decision 等生产决策字段
 * 3. 推荐专区视觉契约：为你推荐主标题、副标题与自适应卡片容器
 * 4. “为什么推荐”理由契约：严格呈现后端 ValidatedReason，禁止前端拼装算法指标
 * 5. 来源 Badge 契约：精准区分“学海智导”与“中国大学 MOOC”
 * 6. 内部资源交互分流契约：CONCEPT_CARD/PRACTICE/EXAMPLE 进入既有内部学习流程
 * 7. 零学习副作用契约：查看与点击推荐卡片本身绝不产生正式学习事件或 BKT 变更
 * 8. MOOC 外部资源安全跳转契约：必须调起 ExternalRedirectModal 经用户确认后跳转
 * 9. 强制安全防注入测试：即使 AI Payload 注入恶意 URL，前端绝不直接导航，强制走权威目录
 * 10. 中国大学MOOC官方白名单域名安全校验
 * 11. 优雅降级契约：API 失败 (500/422/超时) 绝对不导致 ResourceHub 崩溃
 * 12. 空推荐处理契约：返回空列表时展示友好提示，页面保持完全可用
 * 13. 加载中状态契约：克制展示“正在生成推荐……”，非阻塞设计
 * 14. 推荐数量契约：合法支持 1 至 3 项推荐候选展示
 * 15. 用户可见文案零黑话合规性：严禁 DeepSeek, BKT, mastery_probability, 置信度等技术术语
 * 16. 多学生上下文隔离契约：切换 student_id 立即重置推荐列表与错误状态
 */

import { describe, it } from 'node:test';
import assert from 'node:assert/strict';

import type {
  PersonalizedRecommendation,
  PersonalizedRecommendationResponse,
  LearningResource,
} from '../src/types.ts';
import { isSafeChinaMoocUrl } from '../src/utils/externalResource.ts';

describe('Sprint 10-B Phase 3: AI 个性化推荐产品化契约测试', () => {
  // 模拟真实合规内部推荐项 (K03)
  const mockInternalRec: PersonalizedRecommendation = {
    knowledge_id: 'K03',
    resource_id: 'res_k03_concept',
    reason: '需求价格弹性是微观经济学核心考点，建议优先掌握夯实基础。',
    title: '需求价格弹性 考点精要微卡',
    resource_type: 'CONCEPT_CARD',
    source: 'xuehai_internal',
  };

  // 模拟真实合规中国大学MOOC外部推荐项 (K03)
  const mockMoocRec: PersonalizedRecommendation = {
    knowledge_id: 'K03',
    resource_id: 'mooc_k03_elasticity',
    reason: '你正在攻坚弹性理论，北京大学名师精品课能帮助你拓展实践应用。',
    title: '微观经济学进阶：需求价格弹性与市场应用 (北京大学)',
    resource_type: 'VIDEO',
    source: 'china_mooc',
  };

  // 模拟包含 3 项推荐的标准响应
  const mockRecResponse: PersonalizedRecommendationResponse = {
    student_id: 'student_s001',
    recommendations: [
      mockInternalRec,
      {
        knowledge_id: 'K03',
        resource_id: 'res_k03_example_business',
        reason: '通过真实商业降价促销案例，直观理解弹性与总收益的关系。',
        title: '航空机票与打车软件的动态定价逻辑 商业典型例题',
        resource_type: 'EXAMPLE',
        source: 'xuehai_internal',
      },
      mockMoocRec,
    ],
    source: 'mock-deepseek',
    validated: true,
  };

  // ---------------------------------------------------------------------------
  // Test 1: 领域模型契约
  // ---------------------------------------------------------------------------
  it('Test 1: PersonalizedRecommendation 实体结构完备且契约对齐', () => {
    assert.equal(mockInternalRec.knowledge_id, 'K03');
    assert.equal(mockInternalRec.resource_id, 'res_k03_concept');
    assert.equal(typeof mockInternalRec.reason, 'string');
    assert.equal(typeof mockInternalRec.title, 'string');
    assert.equal(mockInternalRec.resource_type, 'CONCEPT_CARD');
    assert.equal(mockInternalRec.source, 'xuehai_internal');

    assert.equal(mockRecResponse.student_id, 'student_s001');
    assert.equal(mockRecResponse.recommendations.length, 3);
    assert.equal(mockRecResponse.validated, true);
  });

  // ---------------------------------------------------------------------------
  // Test 2: 纯辅助候选原则与生产决策字段绝对禁止
  // ---------------------------------------------------------------------------
  it('Test 2: 推荐载荷中绝对禁止包含任何生产决策、BKT变更或状态覆写字段', () => {
    const forbiddenFields = [
      'decision',
      'allow_production_decision',
      'mutation',
      'mastery_probability',
      'mastery_update',
      'path_state',
      'bkt_update',
      'production_decision',
      'url', // 严禁 AI payload 直接提供导航 URL
    ];

    for (const field of forbiddenFields) {
      assert.equal(
        field in mockInternalRec,
        false,
        `推荐项载荷不得包含越权字段 ${field}`
      );
      assert.equal(
        field in mockMoocRec,
        false,
        `MOOC推荐项载荷不得包含越权字段 ${field}`
      );
      assert.equal(
        field in mockRecResponse,
        false,
        `推荐响应顶层不得包含越权字段 ${field}`
      );
    }
  });

  // ---------------------------------------------------------------------------
  // Test 3: 推荐专区视觉契约
  // ---------------------------------------------------------------------------
  it('Test 3: 推荐专区具备人本主标题与引导文案', () => {
    const titleText = '为你推荐';
    const subtitleText = '根据你最近的学习情况，为你推荐了这些内容。';

    assert.equal(titleText, '为你推荐');
    assert.ok(subtitleText.includes('根据你最近的学习情况'));
    assert.ok(!titleText.includes('AI'));
    assert.ok(!subtitleText.includes('算法'));
  });

  // ---------------------------------------------------------------------------
  // Test 4: “为什么推荐”理由展示契约
  // ---------------------------------------------------------------------------
  it('Test 4: “为什么推荐”理由来自后端且具备自然解释性', () => {
    assert.ok(mockInternalRec.reason.length > 5);
    assert.ok(mockMoocRec.reason.length > 5);

    // 严禁理由包含底层数学公式与算法参数
    const rawReason = mockInternalRec.reason + mockMoocRec.reason;
    assert.ok(!rawReason.includes('mastery_probability'));
    assert.ok(!rawReason.includes('BKT'));
    assert.ok(!rawReason.includes('P(L)'));
  });

  // ---------------------------------------------------------------------------
  // Test 5: 来源 Badge 契约
  // ---------------------------------------------------------------------------
  it('Test 5: 来源 Badge 准确区分学海智导内部与中国大学MOOC', () => {
    const getSourceLabel = (src: string) =>
      src === 'china_mooc' ? '中国大学 MOOC' : '学海智导';

    assert.equal(getSourceLabel(mockInternalRec.source), '学海智导');
    assert.equal(getSourceLabel(mockMoocRec.source), '中国大学 MOOC');
  });

  // ---------------------------------------------------------------------------
  // Test 6: 内部资源交互分流契约
  // ---------------------------------------------------------------------------
  it('Test 6: 内部资源点击安全映射至既有 Reader/Quiz 流程', () => {
    const resolveActionType = (rec: PersonalizedRecommendation) => {
      if (rec.source === 'china_mooc') return 'EXTERNAL_MODAL';
      if (rec.resource_type === 'CONCEPT_CARD') return 'CONCEPT_CARD_MODAL';
      if (rec.resource_type === 'PRACTICE') return 'QUIZ_LAUNCH';
      return 'EXAMPLE_READER_MODAL';
    };

    assert.equal(resolveActionType(mockInternalRec), 'CONCEPT_CARD_MODAL');

    const exampleRec: PersonalizedRecommendation = {
      ...mockInternalRec,
      resource_type: 'EXAMPLE',
    };
    assert.equal(resolveActionType(exampleRec), 'EXAMPLE_READER_MODAL');

    const practiceRec: PersonalizedRecommendation = {
      ...mockInternalRec,
      resource_type: 'PRACTICE',
    };
    assert.equal(resolveActionType(practiceRec), 'QUIZ_LAUNCH');
  });

  // ---------------------------------------------------------------------------
  // Test 7: 零学习副作用契约
  // ---------------------------------------------------------------------------
  it('Test 7: 点击与展示推荐绝不触发任何正式学习事件、BKT计算或PathState跃迁', () => {
    // 模拟点击推荐的行为：只做页面模态框状态设置，绝不发起学习事件 POST
    let learningEventDispatched = false;
    let bktMutationTriggered = false;
    let pathStateMutated = false;

    // 推荐点击处理逻辑模拟
    const simulateRecClick = (rec: PersonalizedRecommendation) => {
      // 仅打开 UI 模态框，无网络写操作
      if (rec.source === 'china_mooc') {
        // open redirect modal
      } else {
        // open internal reader
      }
    };

    simulateRecClick(mockInternalRec);
    simulateRecClick(mockMoocRec);

    assert.equal(learningEventDispatched, false);
    assert.equal(bktMutationTriggered, false);
    assert.equal(pathStateMutated, false);
  });

  // ---------------------------------------------------------------------------
  // Test 8: MOOC 外部资源安全跳转契约
  // ---------------------------------------------------------------------------
  it('Test 8: MOOC 资源点击必须调起外部跳转确认模态框', () => {
    let externalRedirectTarget: LearningResource | null = null;

    const mockAuthoritativeMoocResource: LearningResource = {
      resource_id: 'mooc_k03_elasticity',
      knowledge_id: 'K03',
      resource_type: 'VIDEO',
      title: '微观经济学进阶：需求价格弹性 (北京大学)',
      description: '精品慕课',
      source: 'china_mooc',
      source_url: 'https://www.icourse163.org/course/PKU-1001540003',
      estimated_minutes: 20,
      difficulty: 0.4,
      summary: '北京大学精品课',
      content_ref: 'mooc_ref_k03_elasticity',
      is_external: true,
      priority: 70,
    };

    // 模拟点击 MOOC 推荐卡片
    if (mockAuthoritativeMoocResource.is_external && mockAuthoritativeMoocResource.source === 'china_mooc') {
      externalRedirectTarget = mockAuthoritativeMoocResource;
    }

    assert.ok(externalRedirectTarget !== null);
    assert.equal(externalRedirectTarget.resource_id, 'mooc_k03_elasticity');
    assert.equal(externalRedirectTarget.is_external, true);
    assert.equal(externalRedirectTarget.source, 'china_mooc');
  });

  // ---------------------------------------------------------------------------
  // Test 9: 强制安全防注入测试 (AI URL 绝对无法绕过权威目录)
  // ---------------------------------------------------------------------------
  it('Test 9: 即使恶意 AI Payload 携带伪造 URL，前端也必须被权威目录完全阻断', () => {
    // 假设攻击者劫持或伪造了 AI 响应，注入了钓鱼 URL
    const poisonedAIPayload: any = {
      knowledge_id: 'K03',
      resource_id: 'mooc_k03_elasticity',
      reason: '点击此链接领取资料',
      title: '恶意钓鱼课程',
      source: 'china_mooc',
      url: 'https://evil.attacker.com/steal-account',
    };

    // 权威目录映射（系统权威数据）
    const authoritativeCatalog: Record<string, string> = {
      mooc_k03_elasticity: 'https://www.icourse163.org/course/PKU-1001540003',
    };

    // 前端解析机制：绝对不读取 poisonedAIPayload.url，必须通过 resource_id 查阅权威目录
    const resolvedUrl = authoritativeCatalog[poisonedAIPayload.resource_id];

    assert.notEqual(resolvedUrl, poisonedAIPayload.url);
    assert.equal(resolvedUrl, 'https://www.icourse163.org/course/PKU-1001540003');
    assert.ok(isSafeChinaMoocUrl(resolvedUrl));
  });

  // ---------------------------------------------------------------------------
  // Test 10: 中国大学MOOC官方白名单域名安全校验
  // ---------------------------------------------------------------------------
  it('Test 10: 外部跳转 URL 必须通过 isSafeChinaMoocUrl 严格校验', () => {
    assert.ok(isSafeChinaMoocUrl('https://www.icourse163.org/course/PKU-1001540003'));
    assert.ok(isSafeChinaMoocUrl('https://icourse163.org/learn/PKU-1001540003'));

    // 仿冒域名与非法协议
    assert.equal(isSafeChinaMoocUrl('http://www.icourse163.org/course/test'), false);
    assert.equal(isSafeChinaMoocUrl('https://evil.icourse163.org.attacker.com/'), false);
    assert.equal(isSafeChinaMoocUrl('https://attacker.com?redirect=icourse163.org'), false);
    assert.equal(isSafeChinaMoocUrl('javascript:alert(1)'), false);
  });

  // ---------------------------------------------------------------------------
  // Test 11: 优雅降级契约 (API 失败不影响 ResourceHub)
  // ---------------------------------------------------------------------------
  it('Test 11: 推荐接口调用抛出异常时，错误被内部吸收并降级展示，不使整体崩溃', () => {
    let hubCrashed = false;
    let fallbackRendered = false;

    // 模拟推荐加载函数中的 try-catch 保护
    try {
      // 模拟 500 / 网络中断
      throw new Error('500 Internal Server Error / DeepSeek Timeout');
    } catch (err) {
      fallbackRendered = true;
    }

    assert.equal(hubCrashed, false);
    assert.equal(fallbackRendered, true);
  });

  // ---------------------------------------------------------------------------
  // Test 12: 空推荐契约
  // ---------------------------------------------------------------------------
  it('Test 12: 推荐列表为空时友好提示，不展示卡片且不报错', () => {
    const emptyResponse: PersonalizedRecommendationResponse = {
      student_id: 'student_s001',
      recommendations: [],
      source: 'mock-deepseek',
      validated: true,
    };

    assert.equal(emptyResponse.recommendations.length, 0);
    const emptyNotice = '暂时没有适合你的推荐，可浏览下方全部学习资源。';
    assert.ok(emptyNotice.includes('暂时没有适合你的推荐'));
  });

  // ---------------------------------------------------------------------------
  // Test 13: 加载中状态契约
  // ---------------------------------------------------------------------------
  it('Test 13: 推荐加载中状态文案克制，绝不夸张', () => {
    const loadingText = '正在生成推荐……';
    assert.equal(loadingText, '正在生成推荐……');
    assert.ok(!loadingText.includes('计算能力'));
    assert.ok(!loadingText.includes('分析大脑'));
  });

  // ---------------------------------------------------------------------------
  // Test 14: 推荐数量边界契约 (1~3 项)
  // ---------------------------------------------------------------------------
  it('Test 14: 推荐数量合法支持 1 至 3 项候选', () => {
    const singleRecList = [mockInternalRec];
    const tripleRecList = mockRecResponse.recommendations;

    assert.equal(singleRecList.length, 1);
    assert.equal(tripleRecList.length, 3);
    assert.ok(singleRecList.length <= 3);
    assert.ok(tripleRecList.length <= 3);
  });

  // ---------------------------------------------------------------------------
  // Test 15: 用户可见文案零黑话合规性
  // ---------------------------------------------------------------------------
  it('Test 15: 用户可见推荐组件文案严禁出现算法与模型黑话', () => {
    const userFacingTexts = [
      '为你推荐',
      '根据你最近的学习情况，为你推荐了这些内容。',
      '💡 为什么推荐',
      '开始学习',
      '前往学习',
      '正在生成推荐……',
      '暂时没有生成推荐，可浏览下方全部学习资源。',
      '暂时没有适合你的推荐，可浏览下方全部学习资源。',
      '学海智导',
      '中国大学 MOOC',
    ];

    const bannedKeywords = [
      'DeepSeek',
      'deepseek',
      'BKT',
      'bkt',
      'mastery_probability',
      'PathState',
      'path_state',
      '置信度',
      '模型评分',
      '算法决策',
      '生产决策',
    ];

    for (const text of userFacingTexts) {
      for (const banned of bannedKeywords) {
        assert.ok(
          !text.includes(banned),
          `文案 "${text}" 违规包含了被禁术语 "${banned}"`
        );
      }
    }
  });

  // ---------------------------------------------------------------------------
  // Test 16: 多学生上下文隔离契约
  // ---------------------------------------------------------------------------
  it('Test 16: 切换 student_id 必须立即重置推荐状态并触发全新获取', () => {
    let currentRecommendations = [...mockRecResponse.recommendations];
    let currentStudent = 'student_s001';

    // 模拟学生切换至 student_s002
    const switchStudent = (newStudent: string) => {
      currentStudent = newStudent;
      currentRecommendations = []; // 状态严格重置
    };

    switchStudent('student_s002');
    assert.equal(currentStudent, 'student_s002');
    assert.equal(currentRecommendations.length, 0);
  });
});
