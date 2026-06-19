"""定时任务调度器（APScheduler）。

每天 REVIEW_PUSH_TIME（默认 07:30）触发 review_service.run_daily_review()，
把昨天记录的知识点推送到配置的通道（Console / WeClaw）。
"""
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from config import REVIEW_PUSH_TIME

logger = logging.getLogger("kaoyan.scheduler")

_scheduler: BackgroundScheduler | None = None


def _daily_review_job():
    """每日复盘推送任务。"""
    from services import review_service

    try:
        result = review_service.run_daily_review()
        if result.get("success"):
            logger.info(
                "每日复盘推送成功: %s, %d 条知识点, 通道=%s",
                result.get("date"),
                result.get("count", 0),
                result.get("channel"),
            )
        else:
            logger.error("每日复盘推送失败: %s", result.get("error"))
    except Exception:
        logger.exception("每日复盘任务异常")


def start_scheduler():
    """启动后台调度器（FastAPI startup 时调用）。"""
    global _scheduler
    if _scheduler is not None:
        return _scheduler

    hour, minute = REVIEW_PUSH_TIME
    _scheduler = BackgroundScheduler(timezone="Asia/Shanghai")
    _scheduler.add_job(
        _daily_review_job,
        CronTrigger(hour=hour, minute=minute, timezone="Asia/Shanghai"),
        id="daily_review",
        replace_existing=True,
    )
    _scheduler.start()
    logger.info("调度器已启动，每日 %02d:%02d 推送复盘", hour, minute)
    return _scheduler


def shutdown_scheduler():
    """关闭调度器（FastAPI shutdown 时调用）。"""
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None


def trigger_review_now() -> dict:
    """立即触发一次复盘（手动测试用，给 API 调）。"""
    from services import review_service

    return review_service.run_daily_review()
