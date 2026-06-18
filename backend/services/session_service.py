"""对话会话管理（沿用 自己skills 的设计）。

会话持久化在 chat_sessions / chat_messages 表，支持多轮上下文。
只把 role=user/assistant 的消息当作"可信历史"喂给 LLM。
"""
import json
from typing import Optional

from database import get_connection
from services.ai_service import generate_title

DEFAULT_TITLE = "新对话"


def _row_to_dict(row) -> dict:
    return {
        "id": row["id"],
        "title": row["title"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def get_or_create_session(session_id: Optional[int], first_message: str) -> dict:
    """传入 session_id 则复用，否则新建。"""
    conn = get_connection()
    try:
        if session_id:
            row = conn.execute(
                "SELECT * FROM chat_sessions WHERE id = ?", (session_id,)
            ).fetchone()
            if row:
                return _row_to_dict(row)
        # 新建
        title = generate_title(first_message) if first_message else DEFAULT_TITLE
        cur = conn.execute("INSERT INTO chat_sessions (title) VALUES (?)", (title,))
        conn.commit()
        new_id = cur.lastrowid
        row = conn.execute(
            "SELECT * FROM chat_sessions WHERE id = ?", (new_id,)
        ).fetchone()
        return _row_to_dict(row)
    finally:
        conn.close()


def update_session_title_if_default(session_id: int, message: str) -> None:
    """若会话标题还是默认值，则用首条消息生成一个标题。"""
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT title FROM chat_sessions WHERE id = ?", (session_id,)
        ).fetchone()
        if row and (not row["title"] or row["title"] == DEFAULT_TITLE):
            title = generate_title(message) if message else DEFAULT_TITLE
            conn.execute(
                "UPDATE chat_sessions SET title = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (title, session_id),
            )
            conn.commit()
    finally:
        conn.close()


def add_message(
    session_id: int,
    role: str,
    content: str,
    matched_knowledge: list[dict] | None = None,
    preview: dict | None = None,
    thoughts: list[str] | None = None,
) -> int:
    conn = get_connection()
    try:
        cur = conn.execute(
            """INSERT INTO chat_messages
               (session_id, role, content, matched_knowledge, preview, thoughts)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                session_id,
                role,
                content,
                json.dumps(matched_knowledge or [], ensure_ascii=False),
                json.dumps(preview, ensure_ascii=False) if preview else None,
                json.dumps(thoughts or [], ensure_ascii=False),
            ),
        )
        conn.execute(
            "UPDATE chat_sessions SET updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (session_id,),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def get_trusted_chat_history(session_id: int) -> list[dict]:
    """获取可信对话历史（role=user/assistant 的 content），喂给 LLM。"""
    conn = get_connection()
    try:
        rows = conn.execute(
            """SELECT role, content FROM chat_messages
               WHERE session_id = ? ORDER BY id ASC""",
            (session_id,),
        ).fetchall()
    finally:
        conn.close()
    history = []
    for r in rows:
        if r["role"] in {"user", "assistant"} and r["content"]:
            history.append({"role": r["role"], "content": r["content"]})
    # 保留最近 10 轮，避免 token 爆炸
    return history[-20:]


def list_sessions() -> list[dict]:
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM chat_sessions ORDER BY updated_at DESC LIMIT 50"
        ).fetchall()
        return [_row_to_dict(r) for r in rows]
    finally:
        conn.close()


def get_session(session_id: int) -> Optional[dict]:
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM chat_sessions WHERE id = ?", (session_id,)
        ).fetchone()
        return _row_to_dict(row) if row else None
    finally:
        conn.close()


def delete_session(session_id: int) -> bool:
    conn = get_connection()
    try:
        cur = conn.execute("DELETE FROM chat_sessions WHERE id = ?", (session_id,))
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()
