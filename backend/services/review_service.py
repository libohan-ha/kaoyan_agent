"""复盘服务：拉取昨日记录、生成推送内容、记录推送日志。

复盘逻辑（用户明确要求）：
- 每天 7:30 触发
- 只拉"昨天"创建的知识点（今天的不算）
- 没记录就推送一条"昨天没记录"
- 推送内容 = 原文清单（不转提问式）
"""
import json
from datetime import datetime, date
from typing import Optional

from database import get_connection
from services import knowledge_service


def get_yesterday_knowledge() -> list[dict]:
    """拉昨天的知识点（委托给 knowledge_service）。"""
    return knowledge_service.get_yesterday_knowledge()


def build_review_content(items: list[dict], target_date: Optional[str] = None) -> tuple[str, str]:
    """根据知识点列表生成 (title, markdown_content)。

    Args:
        items: 知识点列表
        target_date: 复盘的目标日期（昨天的日期），用于标题
    """
    yesterday = target_date or (
        datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    )
    if isinstance(yesterday, str):
        date_str = yesterday
    else:
        from datetime import timedelta

        date_str = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

    if not items:
        return (
            f"📚 考研复盘 {date_str}",
            f"**{date_str} 没有新记录哦**\n\n昨天没有记录知识点，今天加油！💪",
        )

    # 按学科分组
    by_subject: dict[str, list[dict]] = {}
    for item in items:
        by_subject.setdefault(item["subject"], []).append(item)

    lines = [f"**📚 {date_str} 考研复盘**", f"昨天共记录 **{len(items)}** 个知识点：\n"]
    for subject, group in by_subject.items():
        lines.append(f"\n### {subject}（{len(group)}）\n")
        for i, item in enumerate(group, 1):
            tags_str = f" `{'` `'.join(item['tags'])}`" if item.get("tags") else ""
            lines.append(f"{i}. {item['content']}{tags_str}")

    title = f"📚 考研复盘 {date_str}（{len(items)}条）"
    return title, "\n".join(lines)


def record_push(knowledge_ids: list[int], review_date: str, channel: str = "console") -> int:
    """记录一次推送到 review_logs，返回 log id。"""
    conn = get_connection()
    try:
        cur = conn.execute(
            """INSERT INTO review_logs (review_date, knowledge_ids, channel)
               VALUES (?, ?, ?)""",
            (review_date, json.dumps(knowledge_ids), channel),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def list_review_logs(limit: int = 20) -> list[dict]:
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM review_logs ORDER BY pushed_at DESC LIMIT ?", (limit,)
        ).fetchall()
        return [
            {
                "id": r["id"],
                "review_date": r["review_date"],
                "knowledge_ids": json.loads(r["knowledge_ids"] or "[]"),
                "pushed_at": r["pushed_at"],
                "channel": r["channel"],
            }
            for r in rows
        ]
    finally:
        conn.close()


def run_daily_review() -> dict:
    """执行一次每日复盘推送（被 scheduler 调用）。

    Returns:
        dict: {success, date, count, channel, title, error?}
    """
    from services.notifier import get_notifier

    items = get_yesterday_knowledge()
    yesterday_str = (datetime.now().replace(microsecond=0)).strftime("%Y-%m-%d")
    # 用昨天日期
    from datetime import timedelta

    yesterday_str = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    title, content = build_review_content(items, yesterday_str)

    notifier = get_notifier()
    try:
        result = notifier.send(title, content)
        record_push([item["id"] for item in items], yesterday_str, channel=notifier.name)
        return {
            "success": True,
            "date": yesterday_str,
            "count": len(items),
            "channel": notifier.name,
            "title": title,
            "send_result": result,
        }
    except Exception as exc:
        record_push([item["id"] for item in items], yesterday_str, channel="error")
        return {
            "success": False,
            "date": yesterday_str,
            "count": len(items),
            "error": str(exc),
        }
