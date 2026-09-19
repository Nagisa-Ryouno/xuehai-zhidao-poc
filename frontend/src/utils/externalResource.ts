/**
 * frontend/src/utils/externalResource.ts
 * 学海智导 (Xuehai Zhidao) — Phase 6 / Sprint 10-A
 * 外部学习资源安全校验与安全跳转工具 (External Resource Security & Navigation)
 *
 * 核心安全规则：
 * 1. 协议严格限定为 HTTPS
 * 2. 域名必须属于中国大学MOOC官方域名范围 (icourse163.org 及其合法子域名)
 * 3. 严禁带有用户名/密码 (userinfo)
 * 4. 严防恶意外域伪造 (如 evil.icourse163.org.attacker.com)
 * 5. 统一使用 window.open(url, '_blank', 'noopener,noreferrer') 安全打开
 */

const ALLOWED_MOOC_DOMAINS = ['icourse163.org'];

/**
 * 校验指定 URL 是否为合法的中国大学MOOC官方安全链接
 *
 * @param url 待校验的 URL 字符串
 * @returns boolean 是否为官方安全链接
 */
export function isSafeChinaMoocUrl(url: string | null | undefined): boolean {
  if (!url || typeof url !== 'string') {
    return false;
  }

  const trimmed = url.trim();
  if (!trimmed) {
    return false;
  }

  try {
    const parsed = new URL(trimmed);

    // 1. 协议必须是 https
    if (parsed.protocol !== 'https:') {
      return false;
    }

    // 2. 严禁包含 credentials (userinfo)
    if (parsed.username || parsed.password) {
      return false;
    }

    // 3. 域名解析与小写化
    const hostname = parsed.hostname.toLowerCase();
    if (!hostname) {
      return false;
    }

    // 4. 严格匹配 icourse163.org 或 *.icourse163.org
    const isMatched = ALLOWED_MOOC_DOMAINS.some(
      (domain) => hostname === domain || hostname.endsWith(`.${domain}`)
    );

    if (!isMatched) {
      return false;
    }

    // 5. 校验端口 (只能是默认 443 或未指定)
    if (parsed.port && parsed.port !== '443') {
      return false;
    }

    return true;
  } catch {
    return false;
  }
}

/**
 * 安全打开中国大学MOOC外部链接
 * 在执行 window.open 前进行最终安全防御校验，并使用 noopener,noreferrer
 *
 * @param url 目标链接
 * @returns boolean 是否成功触发安全跳转
 */
export function openExternalMoocUrl(url: string | null | undefined): boolean {
  if (!isSafeChinaMoocUrl(url)) {
    console.warn('[Security] Refused to open unsafe or non-MOOC URL:', url);
    return false;
  }

  if (typeof window !== 'undefined' && typeof window.open === 'function') {
    window.open(url as string, '_blank', 'noopener,noreferrer');
    return true;
  }

  return false;
}
