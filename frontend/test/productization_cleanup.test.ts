/**
 * productization_cleanup.test.ts
 * 学海智导 (Xuehai Zhidao) — Final Productization Cleanup Verification
 *
 * 核心验证：
 * 1. 品牌标题单行不折行契约 (学海智导 Single-line Contract)
 * 2. 彻底移除 AI 状态宣传标签 (AI分析服务在线 / 分析服务离线)
 * 3. 彻底移除内部研发标签 (AI Learning Pilot)
 * 4. 用户名称规范化与 display_name 分离契约 (无 DEMO_ 前缀、无 经济学·正确率 后缀)
 * 5. 头像首字符提取与绝对防溢出契约 (getAvatarInitial Single Character)
 */

import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { getAvatarInitial } from '../src/utils/avatar.ts';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const SRC_DIR = path.resolve(__dirname, '../src');

describe('Final Productization Cleanup: Brand, Status, User Naming & Avatar Hardening', () => {
  // -------------------------------------------------------------
  // 1. Brand 标题单行与无折行布局契约
  // -------------------------------------------------------------
  describe('1. Brand 标题单行排版契约 (学海智导)', () => {
    it('1. Header.tsx 必须为 "学海智导" 配置 whitespace-nowrap 与 flex-shrink-0', () => {
      const headerPath = path.join(SRC_DIR, 'components/Header.tsx');
      const content = fs.readFileSync(headerPath, 'utf-8');

      // 验证 brand 文本存在
      assert.ok(content.includes('学海智导'), 'Header 必须包含核心品牌文字 "学海智导"');

      // 验证紧挨 brand 的类名具备 whitespace-nowrap 与 flex-shrink-0
      const hasNowrap = /<span[^>]*whitespace-nowrap[^>]*>[^<]*学海智导[^<]*<\/span>/s.test(content);
      const hasFlexShrink = /<span[^>]*flex-shrink-0[^>]*>[^<]*学海智导[^<]*<\/span>/s.test(content);

      assert.ok(hasNowrap, '品牌标题 "学海智导" 必须包含 whitespace-nowrap 样式禁止换行');
      assert.ok(hasFlexShrink, '品牌标题 "学海智导" 必须包含 flex-shrink-0 样式防止被右侧压缩');
    });

    it('2. Header.tsx 品牌容器结构必须为 shrink-0，避免小屏幕视口挤压', () => {
      const headerPath = path.join(SRC_DIR, 'components/Header.tsx');
      const content = fs.readFileSync(headerPath, 'utf-8');
      assert.ok(
        content.includes('shrink-0'),
        '品牌区域父容器必须具备 shrink-0 防挤压属性'
      );
    });
  });

  // -------------------------------------------------------------
  // 2. 彻底删除内部状态 UI (AI分析服务在线 / 分析服务离线)
  // -------------------------------------------------------------
  describe('2. 移除内部 AI 分析状态框契约', () => {
    it('1. 前端用户界面代码库中绝对严禁存在 "AI分析服务在线"', () => {
      const filesToCheck = [
        'components/Header.tsx',
        'layouts/StudentLayout.tsx',
        'layouts/TeacherLayout.tsx',
        'components/student/StudentHome.tsx',
      ];

      for (const relPath of filesToCheck) {
        const fullPath = path.join(SRC_DIR, relPath);
        if (fs.existsSync(fullPath)) {
          const content = fs.readFileSync(fullPath, 'utf-8');
          assert.ok(
            !content.includes('AI分析服务在线'),
            `${relPath} 严禁包含 "AI分析服务在线"`
          );
        }
      }
    });

    it('2. 前端用户界面代码库中绝对严禁存在 "分析服务离线"', () => {
      const filesToCheck = [
        'components/Header.tsx',
        'layouts/StudentLayout.tsx',
        'layouts/TeacherLayout.tsx',
        'components/student/StudentHome.tsx',
      ];

      for (const relPath of filesToCheck) {
        const fullPath = path.join(SRC_DIR, relPath);
        if (fs.existsSync(fullPath)) {
          const content = fs.readFileSync(fullPath, 'utf-8');
          assert.ok(
            !content.includes('分析服务离线'),
            `${relPath} 严禁包含 "分析服务离线"`
          );
        }
      }
    });
  });

  // -------------------------------------------------------------
  // 3. 彻底删除内部研发标签 (AI Learning Pilot)
  // -------------------------------------------------------------
  describe('3. 移除内部研发标签契约 (AI Learning Pilot)', () => {
    it('1. 用户界面代码中绝对严禁出现 "AI Learning Pilot" 标签', () => {
      const headerPath = path.join(SRC_DIR, 'components/Header.tsx');
      const content = fs.readFileSync(headerPath, 'utf-8');
      assert.ok(
        !content.includes('AI Learning Pilot'),
        'Header.tsx 严禁出现内部研发标签 "AI Learning Pilot"'
      );
    });
  });

  // -------------------------------------------------------------
  // 4. 用户名称规范化与 display_name 分离契约
  // -------------------------------------------------------------
  describe('4. 用户名称规范化展示契约', () => {
    it('1. Header 学生下拉选择器中不拼接 "经济学 · 正确率" 状态标签', () => {
      const headerPath = path.join(SRC_DIR, 'components/Header.tsx');
      const content = fs.readFileSync(headerPath, 'utf-8');

      // 下拉 option 仅显示学生姓名
      assert.ok(
        !content.includes('stu.major} · 正确率'),
        'Header.tsx 下拉选项中严禁拼接 "经济学 · 正确率"'
      );
      assert.ok(
        !content.includes('{stu.student_id} {stu.student_name}'),
        'Header.tsx 下拉选项中严禁拼接裸 student_id 与姓名'
      );
    });

    it('2. TeacherLayout 下钻上下文不将内部 student_id 直接作为圆形头像文本', () => {
      const teacherPath = path.join(SRC_DIR, 'layouts/TeacherLayout.tsx');
      const content = fs.readFileSync(teacherPath, 'utf-8');

      // 头像容器必须使用 getAvatarInitial，严禁直接塞 {studentId}
      assert.ok(
        !/<div[^>]*w-12 h-12[^>]*>\s*\{studentId\}\s*<\/div>/s.test(content),
        'TeacherLayout 严禁直接把 {studentId} 放入头像圆框'
      );
      assert.ok(
        content.includes('getAvatarInitial'),
        'TeacherLayout 必须调用 getAvatarInitial 渲染首字符'
      );
    });

    it('3. TeacherStudentTable 与 TeacherKnowledgeDiagnosisDrawer 头像使用首字符', () => {
      const tablePath = path.join(SRC_DIR, 'components/teacher/TeacherStudentTable.tsx');
      const drawerPath = path.join(SRC_DIR, 'components/teacher/TeacherKnowledgeDiagnosisDrawer.tsx');

      const tableContent = fs.readFileSync(tablePath, 'utf-8');
      const drawerContent = fs.readFileSync(drawerPath, 'utf-8');

      assert.ok(
        tableContent.includes('getAvatarInitial(st.student_name)'),
        'TeacherStudentTable 必须使用 getAvatarInitial 渲染头像'
      );
      assert.ok(
        drawerContent.includes('getAvatarInitial(st.student_name)'),
        'TeacherKnowledgeDiagnosisDrawer 必须使用 getAvatarInitial 渲染头像'
      );
    });

    it('4. RoleSwitcher 的 title tooltip 不泄露内部 studentId', () => {
      const rsPath = path.join(SRC_DIR, 'components/RoleSwitcher.tsx');
      const content = fs.readFileSync(rsPath, 'utf-8');
      assert.ok(
        !content.includes('${studentId}'),
        'RoleSwitcher tooltip 严禁泄露内部 studentId'
      );
    });
  });

  // -------------------------------------------------------------
  // 5. 头像首字符防溢出工具函数 (getAvatarInitial)
  // -------------------------------------------------------------
  describe('5. 头像首字符提取与绝对防溢出防御契约', () => {
    it('1. 标准中文姓名精准提取首字', () => {
      assert.equal(getAvatarInitial('新同学'), '新');
      assert.equal(getAvatarInitial('张三'), '张');
      assert.equal(getAvatarInitial('李华'), '李');
      assert.equal(getAvatarInitial('诸葛孔明'), '诸');
    });

    it('2. 英文姓名精准提取首字母', () => {
      assert.equal(getAvatarInitial('Nagisa'), 'N');
      assert.equal(getAvatarInitial('Alice'), 'A');
      assert.equal(getAvatarInitial('A'), 'A');
      assert.equal(getAvatarInitial('AB'), 'A');
      assert.equal(getAvatarInitial('bob'), 'b');
    });

    it('3. 超长极端用户名提取单字符且绝不溢出', () => {
      const superLongName = '超级超级超级超级超级长的用户名一二三四五六七八九十';
      const initial = getAvatarInitial(superLongName);
      assert.equal(initial, '超');
      assert.equal(Array.from(initial).length, 1, '长度必须严格为 1 个字符');

      const longAscii = 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa';
      const asciiInit = getAvatarInitial(longAscii);
      assert.equal(asciiInit, 'a');
      assert.equal(Array.from(asciiInit).length, 1, '长度必须严格为 1 个字符');
    });

    it('4. 防御性消除遗留 DEMO_ 前缀与 (经济学...) 脏后缀', () => {
      assert.equal(getAvatarInitial('DEMO_6941 新同学'), '新');
      assert.equal(getAvatarInitial('DEMO_1234 张三'), '张');
      assert.equal(getAvatarInitial('DEMO_9999 新同学(经济学·正确率0.0%)'), '新');
      assert.equal(getAvatarInitial('新同学（经济学）'), '新');
    });

    it('5. 空值、空白与异常输入安全回退到 ？', () => {
      assert.equal(getAvatarInitial(undefined), '？');
      assert.equal(getAvatarInitial(null), '？');
      assert.equal(getAvatarInitial(''), '？');
      assert.equal(getAvatarInitial('   '), '？');
    });
  });
});
