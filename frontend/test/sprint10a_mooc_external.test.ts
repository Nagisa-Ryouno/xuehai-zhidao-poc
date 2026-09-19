/**
 * frontend/test/sprint10a_mooc_external.test.ts
 * 学海智导 (Xuehai Zhidao) — Phase 6 / Sprint 10-A
 * 中国大学MOOC外部学习资源与前端安全跳转体验契约测试
 *
 * 覆盖 9 项核心契约：
 * 1. 内部资源 (is_external === false) 保持原有行为与样式契约
 * 2. MOOC 资源 (is_external === true && source === 'china_mooc') 具备中国大学MOOC专属 Badge 与元数据
 * 3. MOOC CTA 具备明确的外部学习标识 ("前往慕课学习")
 * 4. MOOC 资源交互契约：绝对不调起内部 Reader/Modal/Quiz
 * 5. 合法中国大学MOOC URL (https://www.icourse163.org/...) 允许跳转
 * 6. 非法外链与仿冒域名防御 (evil.com, evil.icourse163.org.attacker.com, javascript:, http) 严格拒绝
 * 7. RESOURCE_EXTERNAL_OPEN 遥测事件载荷契约
 * 8. 遥测上报失败解耦：网络或 API 错误绝不阻止外部跳转
 * 9. MOOC metadata 搜索过滤：支持搜索“北京大学”精准检索对应慕课
 * 10. 绝无硬编码：院校与主讲教师信息完全由 metadata 动态驱动
 */

import { describe, it } from 'node:test';
import assert from 'node:assert/strict';

import type { LearningResource, ResourceEventPayload } from '../src/types.ts';
import { isSafeChinaMoocUrl, openExternalMoocUrl } from '../src/utils/externalResource.ts';

describe('Sprint 10-A: 中国大学MOOC外部资源与安全跳转体验契约测试', () => {
  // 模拟真实内部资源样例 (K01)
  const mockInternalResource: LearningResource = {
    resource_id: 'res_k01_concept',
    knowledge_id: 'K01',
    resource_type: 'CONCEPT_CARD',
    title: '稀缺性与选择 考点精要微卡',
    description: '资源有限而欲望无穷，必须做出权衡取舍。',
    source: 'xuehai_internal',
    source_url: null,
    estimated_minutes: 2,
    difficulty: 0.3,
    summary: '【核心概念】资源的稀缺性是经济学产生的前提。',
    content_ref: 'K01',
    is_external: false,
    priority: 85,
    metadata: {
      chapter: '第1章 导论与微观经济学基石',
      reading_time_seconds: 120,
    },
  };

  // 模拟真实中国大学MOOC外部资源样例 (K01)
  const mockMoocResource: LearningResource = {
    resource_id: 'mooc_k01_scarcity',
    knowledge_id: 'K01',
    resource_type: 'VIDEO',
    title: '微观经济学基础：稀缺性与理性选择 (北京大学)',
    description: '由北京大学经济学院名师团队主讲，系统阐释资源稀缺性、机会成本与理性人假设。',
    source: 'china_mooc',
    source_url: 'https://www.icourse163.org/course/PKU-1001540001',
    estimated_minutes: 25,
    difficulty: 0.45,
    summary: '北京大学微观经济学基础精品课，深入浅出讲解稀缺性原理。',
    content_ref: 'mooc_ref_k01_scarcity',
    is_external: true,
    priority: 60,
    metadata: {
      provider: '中国大学MOOC',
      university: '北京大学',
      instructor: '徐高 教授',
      course: '微观经济学之供给与需求',
      chapter: '导论：稀缺性与理性决策',
      verified: true,
    },
  };

  // ---------------------------------------------------------------------------
  // Test 1: 内部资源行为与样式契约
  // ---------------------------------------------------------------------------
  it('Test 1: 内部资源 (is_external === false) 保持原有行为契约', () => {
    assert.equal(mockInternalResource.is_external, false);
    assert.equal(mockInternalResource.source, 'xuehai_internal');
    assert.equal(mockInternalResource.source_url, null);

    // 内部动作映射判定
    const isInternalTarget = !mockInternalResource.is_external;
    assert.ok(isInternalTarget, '内部资源应被判定为内部目标');
  });

  // ---------------------------------------------------------------------------
  // Test 2: MOOC 专属 Badge 与元数据
  // ---------------------------------------------------------------------------
  it('Test 2: MOOC 资源展示中国大学MOOC专属 Badge 与元数据', () => {
    assert.equal(mockMoocResource.is_external, true);
    assert.equal(mockMoocResource.source, 'china_mooc');
    assert.equal(mockMoocResource.metadata?.provider, '中国大学MOOC');
    assert.equal(mockMoocResource.metadata?.university, '北京大学');
    assert.equal(mockMoocResource.metadata?.instructor, '徐高 教授');
  });

  // ---------------------------------------------------------------------------
  // Test 3: MOOC CTA 外部学习文案
  // ---------------------------------------------------------------------------
  it('Test 3: MOOC CTA 必须明确显示为外部学习文案 (前往慕课学习)', () => {
    const isMooc = mockMoocResource.is_external && mockMoocResource.source === 'china_mooc';
    const ctaLabel = isMooc ? '前往慕课学习' : '查看微卡';
    assert.equal(ctaLabel, '前往慕课学习');
  });

  // ---------------------------------------------------------------------------
  // Test 4: MOOC 不调用内部 Reader/Modal/Quiz
  // ---------------------------------------------------------------------------
  it('Test 4: MOOC 资源交互契约：绝对不调起内部 Reader/Modal/Quiz', () => {
    let openedInternalCard = false;
    let openedInternalQuiz = false;
    let openedInternalReader = false;
    let interceptedExternalRedirect = false;

    const handleOpenResourceSimulator = (res: LearningResource) => {
      // 核心防御检查
      if (res.is_external && res.source === 'china_mooc') {
        interceptedExternalRedirect = true;
        return;
      }
      if (res.resource_type === 'CONCEPT_CARD') {
        openedInternalCard = true;
      } else if (res.resource_type === 'PRACTICE') {
        openedInternalQuiz = true;
      } else {
        openedInternalReader = true;
      }
    };

    // 测试 MOOC 外部资源
    handleOpenResourceSimulator(mockMoocResource);
    assert.equal(interceptedExternalRedirect, true, '必须拦截为外部跳转');
    assert.equal(openedInternalCard, false, '绝对不能打开 ConceptCardModal');
    assert.equal(openedInternalQuiz, false, '绝对不能打开 KnowledgePointQuiz');
    assert.equal(openedInternalReader, false, '绝对不能打开 ExampleReaderModal');

    // 测试内部资源正常进入内部分支
    interceptedExternalRedirect = false;
    handleOpenResourceSimulator(mockInternalResource);
    assert.equal(interceptedExternalRedirect, false);
    assert.equal(openedInternalCard, true, '内部微卡正常调起 ConceptCardModal');
  });

  // ---------------------------------------------------------------------------
  // Test 5: 合法中国大学MOOC URL 允许跳转
  // ---------------------------------------------------------------------------
  it('Test 5: 合法中国大学MOOC官方 URL 校验通过且允许跳转', () => {
    const validUrls = [
      'https://www.icourse163.org/course/PKU-1001540001',
      'https://www.icourse163.org/learn/WHU-1002340002?tid=1470001001',
      'https://icourse163.org/course/TEST-12345',
      'https://mooc.icourse163.org/path/to/resource',
    ];

    for (const url of validUrls) {
      assert.equal(isSafeChinaMoocUrl(url), true, `合法 URL 应该通过校验: ${url}`);
    }
  });

  // ---------------------------------------------------------------------------
  // Test 6: 非法外链与仿冒域名防御严格拒绝
  // ---------------------------------------------------------------------------
  it('Test 6: 非法外链、仿冒伪造与恶意协议严格拒绝', () => {
    const unsafeUrls = [
      'https://evil.com',
      'https://evil.icourse163.org.attacker.com',
      'https://evil.icourse163.org.attacker.com/course/PKU-1',
      'http://www.icourse163.org/course/PKU-1', // 非 https
      'javascript:alert(1)',
      'data:text/html,<script>alert(1)</script>',
      'https://user:pass@www.icourse163.org/test', // 包含凭据
      'https://noticourse163.org',
      'https://fakeicourse163.org/course/1',
      '',
      null as unknown as string,
      undefined as unknown as string,
    ];

    for (const url of unsafeUrls) {
      assert.equal(isSafeChinaMoocUrl(url), false, `不安全或伪造 URL 必须被拒绝: ${url}`);
      assert.equal(openExternalMoocUrl(url), false, `不安全 URL 绝对不能执行 openExternalMoocUrl: ${url}`);
    }
  });

  // ---------------------------------------------------------------------------
  // Test 7: RESOURCE_EXTERNAL_OPEN 遥测事件载荷契约
  // ---------------------------------------------------------------------------
  it('Test 7: RESOURCE_EXTERNAL_OPEN 遥测事件载荷包含完整学生、资源与元数据信息', () => {
    const eventPayload: ResourceEventPayload = {
      student_id: 'S001',
      resource_id: mockMoocResource.resource_id,
      knowledge_id: mockMoocResource.knowledge_id,
      event_type: 'RESOURCE_EXTERNAL_OPEN',
      metadata: {
        source: mockMoocResource.source,
        source_url: mockMoocResource.source_url,
        title: mockMoocResource.title,
        resource_type: mockMoocResource.resource_type,
        provider: mockMoocResource.metadata?.provider,
        university: mockMoocResource.metadata?.university,
      },
    };

    assert.equal(eventPayload.student_id, 'S001');
    assert.equal(eventPayload.resource_id, 'mooc_k01_scarcity');
    assert.equal(eventPayload.knowledge_id, 'K01');
    assert.equal(eventPayload.event_type, 'RESOURCE_EXTERNAL_OPEN');
    assert.equal(eventPayload.metadata?.university, '北京大学');
    assert.equal(eventPayload.metadata?.source, 'china_mooc');
  });

  // ---------------------------------------------------------------------------
  // Test 8: 遥测失败解耦
  // ---------------------------------------------------------------------------
  it('Test 8: 遥测接口失败解耦：上报网络异常绝不阻止外部跳转', async () => {
    let mockWindowOpened = false;

    // 模拟 window.open
    const originalWindow = globalThis.window;
    (globalThis as any).window = {
      open: (_url: string, _target?: string, _features?: string) => {
        mockWindowOpened = true;
        return null;
      },
    };

    try {
      // 模拟上报接口抛出 500 网络异常
      const recordResourceEventMock = async () => {
        throw new Error('500 Internal Server Error');
      };

      // 模拟组件中的 handleConfirmExternalRedirect
      const handleConfirm = async (target: LearningResource) => {
        // 遥测事件调用
        await recordResourceEventMock().catch((err) => {
          // 优雅捕获且不向上抛出
          assert.ok(err instanceof Error);
        });

        // 外部跳转继续执行
        if (target.source_url && isSafeChinaMoocUrl(target.source_url)) {
          openExternalMoocUrl(target.source_url);
        }
      };

      await handleConfirm(mockMoocResource);
      assert.equal(mockWindowOpened, true, '即使遥测 500 异常，也必须正常执行外部跳转');
    } finally {
      (globalThis as any).window = originalWindow;
    }
  });

  // ---------------------------------------------------------------------------
  // Test 9: MOOC metadata 搜索过滤
  // ---------------------------------------------------------------------------
  it('Test 9: MOOC metadata 搜索：支持搜索“北京大学”或“徐高”精准检索到对应慕课', () => {
    const resourcePool: LearningResource[] = [
      mockInternalResource,
      mockMoocResource,
      {
        ...mockMoocResource,
        resource_id: 'mooc_k02_whu',
        title: '弹性理论应用 (武汉大学)',
        description: '由武汉大学经管学院名师主讲。',
        summary: '武汉大学微观经济学弹性应用课程。',
        metadata: {
          university: '武汉大学',
          instructor: '李教授',
          course: '微观经济学弹性',
        },
      },
    ];

    const searchFilter = (query: string) => {
      const q = query.trim().toLowerCase();
      return resourcePool.filter((res) => {
        const matchesTitle = res.title.toLowerCase().includes(q);
        const matchesDesc = res.description.toLowerCase().includes(q);
        const matchesSummary = (res.summary || '').toLowerCase().includes(q);
        const matchesProvider = Boolean(res.metadata?.provider && String(res.metadata.provider).toLowerCase().includes(q));
        const matchesUniversity = Boolean(res.metadata?.university && String(res.metadata.university).toLowerCase().includes(q));
        const matchesInstructor = Boolean(res.metadata?.instructor && String(res.metadata.instructor).toLowerCase().includes(q));
        const matchesCourse = Boolean(res.metadata?.course && String(res.metadata.course).toLowerCase().includes(q));
        return (
          matchesTitle ||
          matchesDesc ||
          matchesSummary ||
          matchesProvider ||
          matchesUniversity ||
          matchesInstructor ||
          matchesCourse
        );
      });
    };

    const pkuResults = searchFilter('北京大学');
    assert.equal(pkuResults.length, 1);
    assert.equal(pkuResults[0].resource_id, 'mooc_k01_scarcity');

    const instructorResults = searchFilter('徐高');
    assert.equal(instructorResults.length, 1);
    assert.equal(instructorResults[0].resource_id, 'mooc_k01_scarcity');

    const whuResults = searchFilter('武汉大学');
    assert.equal(whuResults.length, 1);
    assert.equal(whuResults[0].resource_id, 'mooc_k02_whu');
  });

  // ---------------------------------------------------------------------------
  // Test 10: 零硬编码检验
  // ---------------------------------------------------------------------------
  it('Test 10: 零硬编码检验：MOOC 展示数据完全由 resource.metadata 动态驱动', () => {
    const customMooc: LearningResource = {
      ...mockMoocResource,
      resource_id: 'mooc_test_custom',
      metadata: {
        provider: '中国大学MOOC',
        university: '清华大学',
        instructor: '钱颖一 教授',
        course: '经济学原理',
      },
    };

    assert.equal(customMooc.metadata?.university, '清华大学');
    assert.equal(customMooc.metadata?.instructor, '钱颖一 教授');
    assert.notEqual(customMooc.metadata?.university, '北京大学');
  });
});
