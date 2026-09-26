/**
 * student.ts
 * 学生展示名称与编号统一映射工具
 *
 * 严格遵循产品化原则：
 * 1. S001~S005 稳定映射为 新同学01 ~ 新同学05
 * 2. 内部 student_id 绝对不可修改，仅用于底层 API 关联与业务逻辑
 * 3. 演示学生 (DEMO_XXXX) 基于 ID 稳定推导编号，杜绝随机数闪烁
 * 4. 真实自定义姓名保留原名，不强制覆写
 */

export const STUDENT_DISPLAY_NAME_MAP: Record<string, string> = {
  S001: '新同学01',
  S002: '新同学02',
  S003: '新同学03',
  S004: '新同学04',
  S005: '新同学05',
};

export function getStudentDisplayName(
  studentId?: string | null,
  rawName?: string | null
): string {
  // 1. 优先使用标准预设学生稳定映射 (S001 ~ S005)
  if (studentId && STUDENT_DISPLAY_NAME_MAP[studentId]) {
    return STUDENT_DISPLAY_NAME_MAP[studentId];
  }

  // 2. 若存在真实自定义姓名且不是通用占位符，保留真实姓名
  if (
    rawName &&
    rawName.trim() &&
    rawName !== '新同学' &&
    !rawName.startsWith('DEMO_')
  ) {
    return rawName.trim();
  }

  // 3. 处理标准 S\d+ 编号 (如 S006, S10)
  if (studentId && /^S(\d+)$/i.test(studentId)) {
    const match = studentId.match(/^S(\d+)$/i);
    if (match) {
      const num = parseInt(match[1], 10);
      return `新同学${num.toString().padStart(2, '0')}`;
    }
  }

  // 4. 处理 DEMO_XXXX 演示学生：基于 ID 稳定计算两位数编号 (10 ~ 99)
  if (studentId && studentId.startsWith('DEMO_')) {
    let hash = 0;
    for (let i = 0; i < studentId.length; i++) {
      hash = (hash * 31 + studentId.charCodeAt(i)) & 0xffffffff;
    }
    const stableNum = (Math.abs(hash) % 90) + 10;
    return `新同学${stableNum}`;
  }

  // 5. 稳定兜底
  if (rawName && rawName.trim()) {
    return rawName.trim();
  }

  return '新同学01';
}
