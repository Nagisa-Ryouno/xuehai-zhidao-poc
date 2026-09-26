/**
 * 头像字符提取与展示统一安全工具
 * 严格遵循产品化原则：
 * 1. 恒定只返回单个字符，杜绝头像框内文字溢出
 * 2. 具备极强防御性，自动消除 DEMO_ 前缀、长用户名与脏后缀
 * 3. 空值稳定降级为 '？'
 */

export function getAvatarInitial(name?: string | null): string {
  if (!name) return '？';
  let clean = String(name).trim();
  if (!clean) return '？';

  // 防御性剔除可能误传的 DEMO_XXXX 前缀
  clean = clean.replace(/^DEMO_\w*\s*/i, '');

  // 防御性剔除可能误传的括号注释，如 (经济学...)
  clean = clean.replace(/[\(（].*?[\)）]/g, '').trim();

  if (!clean) return '？';

  // 使用 Array.from 准确捕获第一个 Unicode 字符（兼容 Emoji 与宽字符）
  const chars = Array.from(clean);
  return chars[0] || '？';
}
