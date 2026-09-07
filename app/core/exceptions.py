# -*- coding: utf-8 -*-
"""
app.core.exceptions
核心业务与领域异常定义 (Pure Python Exceptions - Zero Web Dependency)
"""


class AppException(Exception):
    """基础应用异常"""

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class EntityNotFoundError(AppException):
    """业务实体不存在异常 (对应 HTTP 404)"""
    pass


class InvalidOptionError(AppException):
    """用户提交选项非法异常 (对应 HTTP 422)"""
    pass


class PrerequisiteNotMetError(AppException):
    """前置依赖未满足异常"""
    pass
