# -*- coding: utf-8 -*-
"""
04_api.py
学海智导 (Xuehai Zhidao) - FastAPI 后端入口 (Backward-compatible Facade)

向后兼容门面，统一转接到模块化单体主应用 app.main.app。
"""

from app.main import app

__all__ = [
    "app",
]

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8000,
    )