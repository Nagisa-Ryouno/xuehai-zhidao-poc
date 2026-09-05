# -*- coding: utf-8 -*-
"""
app.main
学海智导 (Xuehai Zhidao) V2 核心 API 入口应用

组织与挂载全部 8 个领域路由，配置跨域 CORS 中间件与全局生命周期。
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routers import (
    assistant,
    events,
    knowledge_graph,
    learning_state,
    path,
    quiz,
    students,
    system,
)


def create_app() -> FastAPI:
    """构建并配置统一的 FastAPI 应用实例"""
    application = FastAPI(
        title="学海智导 API",
        description="学海智导——AI驱动的大学生个性化学习指导平台 V2",
        version="0.2.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # 跨域 CORS 支持
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 注册 8 大领域路由
    application.include_router(system.router)
    application.include_router(students.router)
    application.include_router(path.router)
    application.include_router(knowledge_graph.router)
    application.include_router(assistant.router)
    application.include_router(events.router)
    application.include_router(quiz.router)
    application.include_router(learning_state.router)

    return application


app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
    )
