"""复盘相关路由：查看昨日/今日复盘、手动触发推送、查看推送日志。"""
from fastapi import APIRouter

from services import review_service, knowledge_service
import scheduler

router = APIRouter(prefix="/api/review", tags=["review"])


@router.get("/yesterday")
def yesterday():
    """返回昨天记录的知识点 + 格式化好的复盘内容。"""
    items = review_service.get_yesterday_knowledge()
    title, content = review_service.build_review_content(items)
    return {
        "date": _yesterday_str(),
        "count": len(items),
        "items": items,
        "title": title,
        "content": content,
    }


@router.get("/today")
def today():
    """返回今天记录的知识点（给前端"今日复盘"页用）。"""
    from datetime import datetime

    date_str = datetime.now().strftime("%Y-%m-%d")
    items = knowledge_service.get_by_date(date_str)
    return {"date": date_str, "count": len(items), "items": items}


@router.post("/trigger")
def trigger():
    """手动触发一次复盘推送（测试用，调 scheduler 立即执行）。"""
    result = scheduler.trigger_review_now()
    return result


@router.get("/logs")
def logs(limit: int = 20):
    """查看历史推送记录。"""
    return {"logs": review_service.list_review_logs(limit)}


def _yesterday_str() -> str:
    from datetime import datetime, timedelta

    return (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
