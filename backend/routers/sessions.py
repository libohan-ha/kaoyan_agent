"""会话管理路由（列表 / 详情 / 删除）。"""
import json

from fastapi import APIRouter, HTTPException

from models import SessionCreateRequest, SessionMessageCreateRequest
from services import session_service

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


@router.get("")
def list_sessions():
    return {"sessions": session_service.list_sessions()}


@router.post("")
def create_session(req: SessionCreateRequest):
    """新建空会话。"""
    from database import get_connection

    title = req.title or "新对话"
    conn = get_connection()
    try:
        cur = conn.execute("INSERT INTO chat_sessions (title) VALUES (?)", (title,))
        conn.commit()
        new_id = cur.lastrowid
        row = conn.execute("SELECT * FROM chat_sessions WHERE id = ?", (new_id,)).fetchone()
        return session_service._row_to_dict(row)
    finally:
        conn.close()


@router.get("/{session_id}")
def get_session(session_id: int):
    session = session_service.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"会话 {session_id} 不存在")
    # 附带消息列表
    from database import get_connection

    conn = get_connection()
    try:
        rows = conn.execute(
            """SELECT * FROM chat_messages WHERE session_id = ? ORDER BY id ASC""",
            (session_id,),
        ).fetchall()
    finally:
        conn.close()
    messages = []
    for r in rows:
        messages.append(
            {
                "id": r["id"],
                "role": r["role"],
                "content": r["content"],
                "matched_knowledge": json.loads(r["matched_knowledge"] or "[]"),
                "preview": json.loads(r["preview"]) if r["preview"] else None,
                "thoughts": json.loads(r["thoughts"] or "[]"),
                "created_at": r["created_at"],
            }
        )
    return {"session": session, "messages": messages}


@router.delete("/{session_id}")
def delete_session(session_id: int):
    ok = session_service.delete_session(session_id)
    if not ok:
        raise HTTPException(status_code=404, detail=f"会话 {session_id} 不存在")
    return {"ok": True, "id": session_id}
