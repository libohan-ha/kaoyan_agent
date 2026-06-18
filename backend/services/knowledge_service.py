"""知识点业务逻辑层：CRUD + 语义检索 + 去重。

保存流程：写入 knowledge 表 → 生成 embedding → 写入 knowledge_vec 虚拟表。
检索流程：query → embedding → sqlite-vec 检索 → 返回带分数的列表。
"""
import hashlib
import json
import re
from typing import Optional

from database import get_connection
from services import embedding_service
from services.time_utils import local_date_bounds_utc, to_local_display, yesterday_str


def _content_hash(content: str) -> str:
    return hashlib.sha1(content.strip().encode("utf-8")).hexdigest()


def _row_to_dict(row) -> dict:
    return {
        "id": row["id"],
        "content": row["content"],
        "subject": row["subject"],
        "tags": json.loads(row["tags"] or "[]"),
        "source": row["source"],
        "created_at": to_local_display(row["created_at"]),
        "updated_at": to_local_display(row["updated_at"]),
    }


# ===== 创建 =====
def create_knowledge(
    content: str,
    subject: str,
    tags: list[str],
    source: str = "manual",
) -> dict:
    """新建知识点。生成 embedding 并写入向量表。若 content_hash 已存在则返回旧的。"""
    chash = _content_hash(content)
    conn = get_connection()
    try:
        # 去重：同内容（未软删）已存在则直接返回
        existing = conn.execute(
            "SELECT * FROM knowledge WHERE content_hash = ? AND deleted_at IS NULL",
            (chash,),
        ).fetchone()
        if existing:
            return _row_to_dict(existing)

        cursor = conn.execute(
            """INSERT INTO knowledge (content, subject, tags, source, content_hash)
               VALUES (?, ?, ?, ?, ?)""",
            (content.strip(), subject, json.dumps(tags, ensure_ascii=False), source, chash),
        )
        kid = cursor.lastrowid
        conn.commit()
    finally:
        conn.close()

    # 生成 embedding 并写入向量表（在连接外做，避免长事务）
    embedding = embedding_service.get_embedding(content)
    embedding_service.upsert_vector(kid, embedding)

    return get_knowledge_by_id(kid)


def get_knowledge_by_id(kid: int) -> Optional[dict]:
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM knowledge WHERE id = ? AND deleted_at IS NULL", (kid,)
        ).fetchone()
        return _row_to_dict(row) if row else None
    finally:
        conn.close()


# ===== 检索 =====
def search_by_query(query: str, top_k: int = 8, subject: Optional[str] = None) -> list[dict]:
    """语义检索：query → embedding → sqlite-vec 检索 top_k。

    Args:
        query: 用户的问题/描述（会先清洗）
        top_k: 返回条数
        subject: 学科过滤（在结果层做，因为 sqlite-vec JOIN 后过滤更简单）
    """
    clean_q = clean_search_query(query)
    if not clean_q:
        return []
    embedding = embedding_service.get_embedding(clean_q)
    # 多取一些以便学科过滤后仍有足够数量
    fetch_n = top_k * 3 if subject else top_k
    results = embedding_service.search_similar(embedding, top_k=fetch_n)
    if subject:
        results = [r for r in results if r["subject"] == subject]
    return results[:top_k]


def clean_search_query(query: str) -> str:
    """清洗检索 query：去掉命令式短语（"帮我搜""查一下"等），保留实质内容。"""
    q = (query or "").strip()
    # 去掉前导命令词
    q = re.sub(r"^(帮我|麻烦|请|麻烦你)?(搜(一下|索)?|查(一下)?|找(一下|找)?|检索|看看|查找)\s*", "", q)
    q = re.sub(r"^(相关|有关)\s*", "", q)
    return q.strip()


# ===== 列表 / 筛选 =====
def list_knowledge(
    subject: Optional[str] = None,
    tag: Optional[str] = None,
    date: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    deleted: bool = False,
    limit: int = 100,
) -> list[dict]:
    sql = "SELECT * FROM knowledge WHERE 1=1"
    params: list = []
    if not deleted:
        sql += " AND deleted_at IS NULL"
    else:
        sql += " AND deleted_at IS NOT NULL"
    if subject:
        sql += " AND subject = ?"
        params.append(subject)
    if tag:
        sql += " AND tags LIKE ?"
        params.append(f'%"{tag}"%')
    if date:
        start_utc, end_utc = local_date_bounds_utc(date)
        sql += " AND created_at >= ? AND created_at < ?"
        params.extend([start_utc, end_utc])
    else:
        if date_from:
            start_utc, _ = local_date_bounds_utc(date_from)
            sql += " AND created_at >= ?"
            params.append(start_utc)
        if date_to:
            _, end_utc = local_date_bounds_utc(date_to)
            sql += " AND created_at < ?"
            params.append(end_utc)
    sql += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)

    conn = get_connection()
    try:
        rows = conn.execute(sql, params).fetchall()
        return [_row_to_dict(r) for r in rows]
    finally:
        conn.close()


def get_by_date(date_str: str) -> list[dict]:
    return list_knowledge(date=date_str)


def get_by_date_range(date_from: str, date_to: str) -> list[dict]:
    return list_knowledge(date_from=date_from, date_to=date_to)


def get_by_subject(subject: str, limit: int = 10) -> list[dict]:
    return list_knowledge(subject=subject, limit=limit)


# ===== 昨日记录（复盘用）=====
def get_yesterday_knowledge() -> list[dict]:
    """拉出昨天 00:00 ~ 24:00（本地）创建的知识点。"""
    return get_by_date(yesterday_str())


# ===== 更新 / 删除 =====
def update_knowledge(kid: int, content: str, subject: str, tags: list[str]) -> Optional[dict]:
    old = get_knowledge_by_id(kid)
    if not old:
        return None
    conn = get_connection()
    try:
        conn.execute(
            """UPDATE knowledge
               SET content = ?, subject = ?, tags = ?, content_hash = ?, updated_at = CURRENT_TIMESTAMP
               WHERE id = ?""",
            (
                content.strip(),
                subject,
                json.dumps(tags, ensure_ascii=False),
                _content_hash(content),
                kid,
            ),
        )
        conn.commit()
    finally:
        conn.close()

    # 内容变了要重算 embedding
    if content.strip() != old["content"]:
        embedding = embedding_service.get_embedding(content)
        embedding_service.upsert_vector(kid, embedding)

    return get_knowledge_by_id(kid)


def soft_delete(kid: int) -> bool:
    conn = get_connection()
    try:
        cur = conn.execute(
            "UPDATE knowledge SET deleted_at = CURRENT_TIMESTAMP WHERE id = ? AND deleted_at IS NULL",
            (kid,),
        )
        conn.commit()
        deleted = cur.rowcount > 0
    finally:
        conn.close()
    # 软删后从向量表移除，避免被检索到
    if deleted:
        embedding_service.delete_vector(kid)
    return deleted


def restore(kid: int) -> bool:
    conn = get_connection()
    try:
        cur = conn.execute(
            "UPDATE knowledge SET deleted_at = NULL WHERE id = ? AND deleted_at IS NOT NULL",
            (kid,),
        )
        conn.commit()
        restored = cur.rowcount > 0
    finally:
        conn.close()
    # 恢复后重建向量
    if restored:
        row = get_knowledge_by_id(kid)
        if row:
            embedding = embedding_service.get_embedding(row["content"])
            embedding_service.upsert_vector(kid, embedding)
    return restored


# ===== 标签 / 学科聚合 =====
def get_all_tags() -> list[str]:
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT tags FROM knowledge WHERE deleted_at IS NULL"
        ).fetchall()
    finally:
        conn.close()
    tag_set: set[str] = set()
    for row in rows:
        for t in json.loads(row["tags"] or "[]"):
            if t:
                tag_set.add(t)
    return sorted(tag_set)


def get_subjects() -> list[dict]:
    conn = get_connection()
    try:
        rows = conn.execute("SELECT * FROM subjects ORDER BY id").fetchall()
        return [{"id": r["id"], "name": r["name"], "description": r["description"]} for r in rows]
    finally:
        conn.close()
