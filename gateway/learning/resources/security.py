# -*- coding: utf-8 -*-
"""
gateway.learning.resources.security
===================================
学海智导 (Xuehai Zhidao) — Phase 6 / Sprint 10-A
中国大学MOOC与外部学习资源 URL 安全校验层 (URL Security Validation Layer)

设计规范与安全红线：
1. 强制 HTTPS：所有外部资源必须通过加密协议传输，杜绝明文或伪协议风险；
2. 严苛官方域名白名单：采用标准 urlsplit 结构化解析 hostname，
   仅放行中国大学MOOC (icourse163.org) 官方域名及受信任子域名；
3. 防御开放重定向与 URL 欺骗：
   - 严禁简单使用 endswith("icourse163.org")，防御 attacker.com 伪造后缀；
   - 拦截包含敏感用户信息段 (username:password@) 的混淆 URL；
   - 拦截非标准端口 (仅放行标准 443 或缺省端口)；
   - 拒绝 javascript:、data:、file:、blob: 等攻击载荷；
4. 纯确定性与离线可用：不发起任何外部网络请求，100% 本地确定性执行。
"""

from typing import Optional, Set
from urllib.parse import urlsplit

# 官方基础域名白名单（仅允许中国大学MOOC官方域名）
MOOC_ALLOWED_BASE_DOMAINS: Set[str] = {
    "icourse163.org",
}

# 允许的特定官方子域名（可扩展）
MOOC_ALLOWED_HOSTNAMES: Set[str] = {
    "icourse163.org",
    "www.icourse163.org",
    "study.icourse163.org",
    "mooc.icourse163.org",
    "mobile.icourse163.org",
}


def validate_external_mooc_url(url: Optional[str]) -> bool:
    """
    确定性校验外部中国大学MOOC资源链接的安全性与合规性。
    
    规则：
    1. 非空且为字符串；
    2. 严格 HTTPS 协议 (scheme == 'https')；
    3. 不得包含用户信息 (username / password)；
    4. 端口必须为 None 或 443；
    5. hostname 必须精确匹配官方域名或其有效官方子域名；
    6. 结构完好，无法解析或畸形 URL 均直接拒绝。
    
    :param url: 待检测的 URL 字符串
    :return: True 如果符合官方安全外链标准，否则 False
    """
    if not url or not isinstance(url, str):
        return False

    clean_url = url.strip()
    if not clean_url:
        return False

    # 预检：必须以 https:// 开头（防范 scheme 为空或相对路径绕过）
    if not clean_url.lower().startswith("https://"):
        return False

    try:
        parsed = urlsplit(clean_url)
    except Exception:
        return False

    # 1. 协议严格为 https
    if parsed.scheme.lower() != "https":
        return False

    # 2. 拒绝包含 userinfo (如 https://attacker.com@icourse163.org 或 https://user:pass@...)
    if parsed.username or parsed.password:
        return False

    # 3. 提取 hostname 并标准化 (小写、去除尾随点)
    raw_host = parsed.hostname
    if not raw_host:
        return False
    hostname = raw_host.lower().rstrip(".")
    if not hostname:
        return False

    # 4. 端口安全性：仅允许缺省或标准 HTTPS 443 端口
    try:
        port = parsed.port
        if port is not None and port != 443:
            return False
    except ValueError:
        # 非数字端口或畸形端口格式
        return False

    # 5. 官方域名白名单精准匹配
    # (a) 精确匹配已记录的官方子域名
    if hostname in MOOC_ALLOWED_HOSTNAMES:
        return True

    # (b) 结构化子域名后缀匹配：必须以 .icourse163.org 结尾且属于其下层子域
    for base in MOOC_ALLOWED_BASE_DOMAINS:
        if hostname == base:
            return True
        if hostname.endswith("." + base):
            # 确保不是伪造的前缀点，如 ".evil.icourse163.org" 依然是合法子域名
            # 但 attacker.com 结尾的在 urlsplit 中 hostname 本身就是 attacker.com，不会匹配此处
            return True

    return False


def sanitize_and_validate_mooc_url(url: Optional[str]) -> Optional[str]:
    """
    若 URL 合法安全，返回去除首尾空格后的标准 URL 字符串；否则返回 None。
    """
    if validate_external_mooc_url(url):
        return url.strip() if url else None
    return None
