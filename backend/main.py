"""FastAPI 入口：挂载路由 + 初始化 DB + 启动调度器。"""
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import HOST, PORT, REVIEW_PUSH_TIME, NOTIFIER_CHANNEL
from database import init_db
from routers import knowledge, agent, review, sessions
import scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("kaoyan.main")

app = FastAPI(title="考研 Agent", version="1.0.0")

# CORS（开发期放开，生产可收紧）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 挂载路由
app.include_router(knowledge.router)
app.include_router(agent.router)
app.include_router(review.router)
app.include_router(sessions.router)


@app.on_event("startup")
def startup():
    init_db()
    scheduler.start_scheduler()
    logger.info("考研 Agent 启动完成")
    logger.info("复盘推送时间: %02d:%02d, 通道: %s", *REVIEW_PUSH_TIME, NOTIFIER_CHANNEL)


@app.on_event("shutdown")
def shutdown():
    scheduler.shutdown_scheduler()
    logger.info("考研 Agent 已关闭")


@app.get("/health")
def health():
    return {"status": "ok", "service": "kaoyan-agent"}


@app.get("/")
def root():
    return {
        "service": "考研 Agent",
        "docs": "/docs",
        "health": "/health",
        "endpoints": [
            "POST /api/agent/chat",
            "POST /api/knowledge",
            "POST /api/knowledge/search",
            "GET  /api/knowledge",
            "GET  /api/review/yesterday",
            "POST /api/review/trigger",
            "GET  /api/sessions",
        ],
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host=HOST, port=PORT, reload=False)
