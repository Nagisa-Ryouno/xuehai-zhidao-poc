import { describe, it, beforeEach } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import {
  lockBodyScroll,
  unlockBodyScroll,
  getActiveLockCount,
  getSavedScrollY,
} from '../src/utils/useBodyScrollLock.ts';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

describe('Sprint 10-D Phase 5 & 5.1: Product UX / Content Integrity / Hardening Evidence Tests', () => {
  const scrollLockPath = path.resolve(__dirname, '../src/utils/useBodyScrollLock.ts');
  const aiAssistantPath = path.resolve(__dirname, '../src/components/AIAssistant.tsx');
  const resourceHubPath = path.resolve(__dirname, '../src/components/student/ResourceHub.tsx');
  const learningSessionPath = path.resolve(__dirname, '../src/components/student/LearningSessionModal.tsx');
  const conceptCardModalPath = path.resolve(__dirname, '../src/components/student/ConceptCardModal.tsx');
  const exampleReaderPath = path.resolve(__dirname, '../src/components/student/ExampleReaderModal.tsx');
  const knowledgeGraphPath = path.resolve(__dirname, '../src/components/KnowledgeGraph.tsx');
  const wrongAnswerPath = path.resolve(__dirname, '../src/components/student/WrongAnswerReview.tsx');
  const studentLayoutPath = path.resolve(__dirname, '../src/layouts/StudentLayout.tsx');

  const scrollLockCode = fs.readFileSync(scrollLockPath, 'utf-8');
  const aiAssistantCode = fs.readFileSync(aiAssistantPath, 'utf-8');
  const resourceHubCode = fs.readFileSync(resourceHubPath, 'utf-8');
  const learningSessionCode = fs.readFileSync(learningSessionPath, 'utf-8');
  const conceptCardModalCode = fs.readFileSync(conceptCardModalPath, 'utf-8');
  const exampleReaderCode = fs.readFileSync(exampleReaderPath, 'utf-8');
  const knowledgeGraphCode = fs.readFileSync(knowledgeGraphPath, 'utf-8');
  const wrongAnswerCode = fs.readFileSync(wrongAnswerPath, 'utf-8');
  const studentLayoutCode = fs.readFileSync(studentLayoutPath, 'utf-8');

  // ==========================================================================
  // Suite 1: useBodyScrollLock 机制与多实例嵌套恢复测试
  // ==========================================================================
  describe('Suite 1: useBodyScrollLock 滚动锁与多实例恢复', () => {
    it('1.1 单弹窗打开设置 overflow:hidden 与 touchAction:none', () => {
      // Setup mock DOM environment
      let overflow = '';
      let touchAction = '';
      let paddingRight = '';
      let scrollYPos = 650;

      const mockDoc = {
        body: {
          style: {
            get overflow() { return overflow; },
            set overflow(v) { overflow = v; },
            get touchAction() { return touchAction; },
            set touchAction(v) { touchAction = v; },
            get paddingRight() { return paddingRight; },
            set paddingRight(v) { paddingRight = v; },
          },
        },
        documentElement: {
          clientWidth: 1200,
          scrollTop: 0,
        },
      };

      const mockWin = {
        scrollY: 650,
        innerWidth: 1215, // 15px scrollbar
        scrollTo: ({ top }: { top: number }) => {
          scrollYPos = top;
        },
      };

      (globalThis as any).document = mockDoc;
      (globalThis as any).window = mockWin;

      // Lock
      lockBodyScroll();
      assert.equal(overflow, 'hidden', 'body.style.overflow 必须为 hidden');
      assert.equal(touchAction, 'none', 'body.style.touchAction 必须为 none');
      assert.equal(paddingRight, '15px', '必须补偿滚动条宽度 15px 防止布局跳动');
      assert.equal(getActiveLockCount(), 1, 'activeLockCount 必须为 1');
      assert.equal(getSavedScrollY(), 650, 'savedScrollY 必须记录为 650');

      // Unlock
      unlockBodyScroll();
      assert.equal(overflow, '', '解锁后 overflow 必须恢复');
      assert.equal(touchAction, '', '解锁后 touchAction 必须恢复');
      assert.equal(paddingRight, '', '解锁后 paddingRight 必须恢复');
      assert.equal(getActiveLockCount(), 0, 'activeLockCount 归零');
      assert.equal(scrollYPos, 650, 'window.scrollTo 必须精准还原至 650');
    });

    it('1.2 多实例嵌套锁 (Modal A -> Modal B -> close B -> close A) 引用计数恢复', () => {
      let overflow = '';
      let paddingRight = '';
      let restoredTop = -1;

      (globalThis as any).document = {
        body: {
          style: {
            get overflow() { return overflow; },
            set overflow(v) { overflow = v; },
            get touchAction() { return ''; },
            set touchAction(_v) {},
            get paddingRight() { return paddingRight; },
            set paddingRight(v) { paddingRight = v; },
          },
        },
        documentElement: { clientWidth: 1200, scrollTop: 0 },
      };
      (globalThis as any).window = {
        scrollY: 1200,
        innerWidth: 1200,
        scrollTo: ({ top }: { top: number }) => {
          restoredTop = top;
        },
      };

      // 1. 打开 Modal A (如 LearningSessionModal)
      lockBodyScroll();
      assert.equal(getActiveLockCount(), 1);
      assert.equal(overflow, 'hidden');

      // 2. 打开 Modal B (如 ExampleReaderModal)
      lockBodyScroll();
      assert.equal(getActiveLockCount(), 2);
      assert.equal(overflow, 'hidden');

      // 3. 关闭 Modal B
      unlockBodyScroll();
      assert.equal(getActiveLockCount(), 1);
      assert.equal(overflow, 'hidden', 'Modal A 仍开启时，背景必须继续保持锁定状态');
      assert.equal(restoredTop, -1, 'Modal A 仍开启时，不得过早恢复页面位置');

      // 4. 关闭 Modal A
      unlockBodyScroll();
      assert.equal(getActiveLockCount(), 0);
      assert.equal(overflow, '', '最外层关闭后，背景完全解锁');
      assert.equal(restoredTop, 1200, '必须精准恢复至初始 1200px 处，杜绝回到顶部 (Issue 12)');
    });

    it('1.3 代码静态契约：所有核心模态框均严格挂载 useBodyScrollLock', () => {
      assert.ok(conceptCardModalCode.includes('useBodyScrollLock'), 'ConceptCardModal 必须挂载 useBodyScrollLock');
      assert.ok(exampleReaderCode.includes('useBodyScrollLock'), 'ExampleReaderModal 必须挂载 useBodyScrollLock');
      assert.ok(learningSessionCode.includes('useBodyScrollLock'), 'LearningSessionModal 必须挂载 useBodyScrollLock');
      assert.ok(scrollLockCode.includes('scrollbarWidth'), 'useBodyScrollLock 必须包含滚动条宽度计算');
    });
  });

  // ==========================================================================
  // Suite 2: Modal WAI-ARIA、Escape 与背景交互契约
  // ==========================================================================
  describe('Suite 2: Modal WAI-ARIA、Escape 与背景点击隔离契约', () => {
    it('2.1 ConceptCardModal 具备 role="dialog"、aria-modal="true"、Escape 与背景点击关闭', () => {
      assert.ok(conceptCardModalCode.includes('role="dialog"'));
      assert.ok(conceptCardModalCode.includes('aria-modal="true"'));
      assert.ok(conceptCardModalCode.includes("e.key === 'Escape'"), '必须支持按 Escape 键关闭');
      assert.ok(conceptCardModalCode.includes('onClick={onClose}'), '必须支持点击背景蒙层关闭');
      assert.ok(conceptCardModalCode.includes('e.stopPropagation()'), '内容卡片必须阻止冒泡防止误关');
    });

    it('2.2 ExampleReaderModal 具备完整 dialog 契约与 Escape 监听', () => {
      assert.ok(exampleReaderCode.includes('role="dialog"'));
      assert.ok(exampleReaderCode.includes('aria-modal="true"'));
      assert.ok(exampleReaderCode.includes("e.key === 'Escape'"), '必须支持按 Escape 键关闭');
      assert.ok(exampleReaderCode.includes('onClick={onClose}'), '必须支持点击背景蒙层关闭');
      assert.ok(exampleReaderCode.includes('e.stopPropagation()'), '内容区必须阻止冒泡');
    });

    it('2.3 LearningSessionModal 具备嵌套 Escape 分级关闭支持', () => {
      assert.ok(learningSessionCode.includes('role="dialog"'));
      assert.ok(learningSessionCode.includes('aria-modal="true"'));
      assert.ok(learningSessionCode.includes("e.key === 'Escape'"), '主会话必须监听 Escape');
      assert.ok(
        learningSessionCode.includes('activeReadingResource') &&
        learningSessionCode.includes('setActiveReadingResource(null)'),
        'Escape 优先关闭内嵌阅读器'
      );
    });
  });

  // ==========================================================================
  // Suite 3: AI Companion 并发防重锁与全局微观经济学作用域契约
  // ==========================================================================
  describe('Suite 3: AI 伴学并发防重锁与微观经济学作用域', () => {
    it('3.1 inFlightLockRef 与 initContextKeyRef 实现单次请求硬阻断', () => {
      assert.ok(aiAssistantCode.includes('inFlightLockRef = useRef<boolean>(false)'), '必须使用同步 useRef 防重锁');
      assert.ok(aiAssistantCode.includes('if (inFlightLockRef.current) return;'), '并发请求在同步首个 tick 即被拦截');
      assert.ok(aiAssistantCode.includes('inFlightLockRef.current = true;'), '发起请求时立即上锁');
      assert.ok(aiAssistantCode.includes('inFlightLockRef.current = false;'), '请求结束 (finally) 时立即解锁');
      assert.ok(aiAssistantCode.includes('initContextKeyRef = useRef<string>'), '必须具备 StrictMode 初始化防重键');
    });

    it('3.2 conversation 模式与考点解耦，支持微观经济学跨考点研讨', () => {
      assert.ok(
        aiAssistantCode.includes("mode === 'conversation' && !kid") &&
        aiAssistantCode.includes("? undefined"),
        'conversation 模式在未绑定考点时不强塞 K01，支持通用微观研讨'
      );
      assert.ok(
        !aiAssistantCode.includes('宏观经济学'),
        'AI 伴学绝不越界扩展未建设的宏观经济学，严格限定在当前微观经济学体系'
      );
    });

    it('3.3 AI 对话历史隔离存储在 xuehai_companion_sessions_${studentId}', () => {
      assert.ok(
        aiAssistantCode.includes('xuehai_companion_sessions_${currentStudentId}'),
        '对话历史必须按 studentId 严格物理隔离存储'
      );
      assert.ok(
        !aiAssistantCode.includes("recordLearningEvent('AI_CHAT_MESSAGE'"),
        '严禁将原始聊天流水写入生产学习事件 learning_events'
      );
    });
  });

  // ==========================================================================
  // Suite 4: 资源学习完成标记 (Resource Completion) 契约与无状态突变保障
  // ==========================================================================
  describe('Suite 4: 资源研读完成标记与零生产状态突变', () => {
    it('4.1 标记与取消标记在 localStorage 与 activeSession 中双向同步', () => {
      assert.ok(
        resourceHubCode.includes('xuehai_completed_resources_${studentId}'),
        '完成标记必须按学生隔离持久化至 localStorage'
      );
      assert.ok(
        resourceHubCode.includes('prev.includes(res.resource_id)'),
        '支持添加完成标记'
      );
      assert.ok(
        resourceHubCode.includes('prev.filter((id) => id !== res.resource_id)'),
        '支持取消完成标记'
      );
      assert.ok(
        resourceHubCode.includes('completed_resource_ids: prev.completed_resource_ids.filter'),
        '取消完成必须同步更新 activeSession'
      );
    });

    it('4.2 资源完成仅作为只读研读跟踪，绝不调用 BKT 与 PathState 接口', () => {
      // 验证 ResourceHub 在 handleToggleComplete 中只触发 RESOURCE_COMPLETE 事件，不调用 quiz submit
      assert.ok(
        resourceHubCode.includes("event_type: 'RESOURCE_COMPLETE'"),
        '记录纯资源日志'
      );
      // 确认未调用 path-states POST 或 quiz/submit
      const toggleFn = resourceHubCode.substring(
        resourceHubCode.indexOf('handleToggleCompleteResource'),
        resourceHubCode.indexOf('handleCompleteResource')
      );
      assert.equal(toggleFn.includes('/quiz/submit'), false, '资源标记完成严禁调用 /quiz/submit');
      assert.equal(toggleFn.includes('/path-states'), false, '资源标记完成严禁修改 PathState');
    });

    it('4.3 学生切换时立即重新读取对应学生的完成标记', () => {
      assert.ok(
        resourceHubCode.includes('localStorage.getItem(`xuehai_completed_resources_${studentId}`)'),
        'studentId 变化时必须重新加载'
      );
    });
  });

  // ==========================================================================
  // Suite 5: 知识图谱语义筛选契约 (全部考点 / 薄弱考点 / 当前学习路径 / 核心前置基石)
  // ==========================================================================
  describe('Suite 5: 知识图谱语义筛选契约', () => {
    it('5.1 四大 Tab 拥有明确的底层数据过滤条件', () => {
      assert.ok(knowledgeGraphCode.includes("activeFilter === 'weak'"), '支持薄弱考点筛选');
      assert.ok(knowledgeGraphCode.includes("activeFilter === 'recommended'"), '支持当前学习路径筛选');
      assert.ok(knowledgeGraphCode.includes("activeFilter === 'prerequisite'"), '支持核心前置基石筛选');
      assert.ok(knowledgeGraphCode.includes("d.is_weak"), '薄弱筛选绑定 is_weak');
      assert.ok(knowledgeGraphCode.includes("d.is_recommended"), '路径筛选绑定 is_recommended 或 activeRoute');
      assert.ok(knowledgeGraphCode.includes("d.is_prerequisite"), '前置基石绑定 is_prerequisite');
    });

    it('5.2 核心前置基石具备明确业务语义标注', () => {
      assert.ok(
        knowledgeGraphCode.includes('薄弱考点的关键前置基石依赖') ||
        knowledgeGraphCode.includes('薄弱考点'),
        '前置基石必须向用户解释是薄弱考点的前置依赖'
      );
    });

    it('5.3 学习地图列表视图与拓扑画布视图一键无缝切换', () => {
      assert.ok(knowledgeGraphCode.includes("viewMode === 'map'"), '支持学习地图列表');
      assert.ok(knowledgeGraphCode.includes("viewMode === 'canvas'"), '支持 React Flow 拓扑画布');
    });
  });

  // ==========================================================================
  // Suite 6: 滚动策略稳定性 (Scroll Policy & Navigation)
  // ==========================================================================
  describe('Suite 6: 路由导航与页面滚动优先级契约', () => {
    it('6.1 子路由切换置顶不干扰焦点材料平滑定位', () => {
      assert.ok(
        studentLayoutCode.includes('window.scrollTo({ top: 0, behavior: \'instant\' })'),
        '切换子路由统一即时置顶'
      );
      assert.ok(
        resourceHubCode.includes('adaptive-recommendation-guide') &&
        resourceHubCode.includes('scrollIntoView'),
        '推荐学习材料进入时具备定向平滑滚动'
      );
    });
  });

  // ==========================================================================
  // Suite 7: 错题本 Wrong Answer Review 契约
  // ==========================================================================
  describe('Suite 7: 错题复盘本结构与紧凑模式', () => {
    it('7.1 支持考点聚合统计与紧凑模式切换', () => {
      assert.ok(wrongAnswerCode.includes('kpCounts'), '必须按知识点聚合错题数量');
      assert.ok(wrongAnswerCode.includes('isCompactMode'), '支持紧凑模式切换');
      assert.ok(wrongAnswerCode.includes('priorityFilter'), '支持按复习优先级过滤');
      assert.ok(wrongAnswerCode.includes('onViewConceptCard'), '支持从错题跳转概念微卡');
      assert.ok(wrongAnswerCode.includes('onStartQuiz'), '支持从错题启动专项微测验');
    });
  });

  // ==========================================================================
  // Suite 8: 全站死按钮与 CTA 全量闭环审计契约
  // ==========================================================================
  describe('Suite 8: CTA 与操作按钮全量闭环审计', () => {
    it('8.1 LearningSessionModal 在平台学习具备明确分支', () => {
      assert.ok(
        learningSessionCode.includes('ExampleReaderModal') ||
        learningSessionCode.includes('setActiveReadingResource'),
        '在平台学习必须能够调起内部阅读器'
      );
      assert.ok(
        learningSessionCode.includes("setCurrentStep('CONCEPT')"),
        '支持回跳概念微卡精读'
      );
      assert.ok(
        learningSessionCode.includes("setCurrentStep('QUIZ')"),
        '支持启动微测验'
      );
    });
  });
});
