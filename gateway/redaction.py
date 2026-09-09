# -*- coding: utf-8 -*-
"""
gateway.redaction
学海智导 (Xuehai Zhidao) V2 - Phase 3 / Sprint 7-D
Stage F: 安全脱敏层与敏感数据隔离引擎 (Security Redaction Layer)

设计原则：
1. 白名单与阻断并重：严格拦截任何敏感字段（API Key、Prompt 全文、Response 全文、学情实体）
2. 递归深度防御：防范通过嵌套 dict、嵌套 list 绕过脱敏
3. 异常文本净化：防范底层异常携带敏感 URL、主机端口、文件路径或 Secret
4. 纯函数与确定性：无副作用，不污染外部业务上下文
"""

import re
from typing import Any, Dict, List, Set, Union

# 严禁进入日志或审计事件的敏感字段名（小写匹配）
SENSITIVE_FIELD_NAMES: Set[str] = {
    "api_key",
    "apikey",
    "authorization",
    "auth",
    "password",
    "secret",
    "token",
    "bearer",
    "prompt",
    "system_prompt",
    "user_prompt",
    "raw_response",
    "answer",
    "learning_context",
    "user_question",
    "stacktrace",
    "traceback",
    "file_path",
    "filepath",
    "cookie",
    "cookies",
    "headers",
    "environment_variables",
    "env",
}

# 敏感模式正则编译
TOKEN_PATTERNS = [
    re.compile(r"sk-proj-[A-Za-z0-9_\-\.]+", re.IGNORECASE),
    re.compile(r"sk-ant-[A-Za-z0-9_\-\.]+", re.IGNORECASE),
    re.compile(r"Bearer\s+[A-Za-z0-9_\-\.]+", re.IGNORECASE),
    re.compile(r"TEST_SECRET_DO_NOT_USE_[A-Za-z0-9_]+", re.IGNORECASE),
]

URL_PATTERN = re.compile(r"https?://[A-Za-z0-9_\-\.:]+", re.IGNORECASE)
FILE_PATH_PATTERN_WIN = re.compile(r"[A-Za-z]:\\[^ \n\r\t]+\.py", re.IGNORECASE)
FILE_PATH_PATTERN_UNIX = re.compile(r"/(?:[a-zA-Z0-9_\-\.]+/)+[a-zA-Z0-9_\-\.]+\.py")
TRACEBACK_PATTERN = re.compile(r"Traceback \(most recent call last\):.*", re.DOTALL | re.IGNORECASE)


def redact_sensitive_string(text: str) -> str:
    """
    对普通字符串进行深度脱敏，擦除凭证、URL、路径与堆栈信息
    """
    if not isinstance(text, str):
        return str(text)

    sanitized = text

    # 1. 擦除已知 Token/Secret
    for pattern in TOKEN_PATTERNS:
        sanitized = pattern.sub("[REDACTED_SECRET]", sanitized)

    # 2. 擦除 URL 与端点主机端口
    sanitized = URL_PATTERN.sub("[REDACTED_ENDPOINT]", sanitized)

    # 3. 擦除源码文件路径
    sanitized = FILE_PATH_PATTERN_WIN.sub("[REDACTED_PATH]", sanitized)
    sanitized = FILE_PATH_PATTERN_UNIX.sub("[REDACTED_PATH]", sanitized)

    # 4. 擦除 Traceback 堆栈
    if "Traceback" in sanitized:
        sanitized = TRACEBACK_PATTERN.sub("[REDACTED_TRACEBACK]", sanitized)

    return sanitized


def sanitize_audit_payload(payload: Any) -> Any:
    """
    递归净化待写入审计事件的数据，过滤敏感字段并对字符串脱敏
    """
    if isinstance(payload, dict):
        cleaned: Dict[str, Any] = {}
        for k, v in payload.items():
            k_lower = str(k).lower().strip()
            # 命中了敏感字段名直接过滤掉，绝不写入
            if k_lower in SENSITIVE_FIELD_NAMES:
                continue
            cleaned[k] = sanitize_audit_payload(v)
        return cleaned
    elif isinstance(payload, list):
        return [sanitize_audit_payload(item) for item in payload]
    elif isinstance(payload, str):
        return redact_sensitive_string(payload)
    else:
        return payload


def sanitize_exception_message(exc: Union[Exception, str]) -> str:
    """
    净化异常消息，确保不泄露任何 Secret、主机端口、文件路径或堆栈细节
    """
    raw_msg = str(exc)
    return redact_sensitive_string(raw_msg)


def mask_secret_token(token: Union[str, None]) -> str:
    """
    将 API Key 转换为脱敏形式，禁止在输出中明文暴露
    """
    if not token:
        return "<UNSET>"
    clean = token.strip()
    if len(clean) <= 8:
        return "***"
    return f"{clean[:3]}...{clean[-4:]}"
