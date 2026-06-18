"""Embedding 服务：硅基流动 bge-m3 + sqlite-vec 向量检索。

- get_embedding(text): 调硅基流动 API 拿 1024 维向量（带内存缓存）
- upsert_vector(knowledge_id, embedding): 写入/更新 sqlite-vec 虚拟表
- search_similar(query, top_k): 向量检索返回 top_k 知识点
"""
import json
import time
import urllib.error
import urllib.request

from config import (
    SILICONFLOW_API_KEY,
    SILICONFLOW_EMBEDDING_MODEL,
    SILICONFLOW_EMBEDDING_TIMEOUT,
    SILICONFLOW_EMBEDDING_URL,
    SEARCH_DEFAULT_TOP_K,
)
from database import get_connection
from services.time_utils import to_local_display

# ===== 内存缓存（短期去重，省 API 调用）=====
_embedding_cache: dict[str, tuple[list[float], float]] = {}
_CACHE_TTL = 300


def _cache_key(text: str) -> str:
    return text[:200]


def get_embedding(text: str) -> list[float]:
    """获取文本的 embedding（带 5 分钟内存缓存）。

    Raises:
        RuntimeError: 缺 key 或 API 调用失败
    """
    key = _cache_key(text)
    cached = _embedding_cache.get(key)
    if cached and time.time() - cached[1] < _CACHE_TTL:
        return cached[0]

    if not SILICONFLOW_API_KEY:
        raise RuntimeError("缺少 SILICONFLOW_API_KEY，无法生成知识点向量")

    result = _call_siliconflow(text)

    _embedding_cache[key] = (result, time.time())
    return result


def _call_siliconflow(text: str) -> list[float]:
    payload = json.dumps(
        {"input": text, "model": SILICONFLOW_EMBEDDING_MODEL}
    ).encode("utf-8")
    request = urllib.request.Request(
        SILICONFLOW_EMBEDDING_URL,
        data=payload,
        headers={
            "Authorization": f"Bearer {SILICONFLOW_API_KEY}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(
            request, timeout=SILICONFLOW_EMBEDDING_TIMEOUT
        ) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Embedding failed: HTTP {exc.code} {body}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Embedding request failed: {exc.reason}") from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError("Embedding response is not valid JSON") from exc

    return _parse_embedding(data)


def _parse_embedding(data: dict) -> list[float]:
    try:
        embedding = data["data"][0]["embedding"]
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError(f"Embedding response missing vector: {data}") from exc
    if not isinstance(embedding, list) or not all(
        isinstance(x, (int, float)) for x in embedding
    ):
        raise RuntimeError(f"Embedding response has invalid vector: {data}")
    return embedding


# ===== sqlite-vec 向量存储与检索 =====
def upsert_vector(knowledge_id: int, embedding: list[float]) -> None:
    """写入或更新某个知识点的向量（用 sqlite-vec）。"""
    blob = _embedding_to_blob(embedding)
    conn = get_connection()
    try:
        # sqlite-vec 用 INSERT OR REPLACE 做 upsert（PRIMARY KEY = knowledge_id）
        conn.execute(
            "INSERT OR REPLACE INTO knowledge_vec(knowledge_id, embedding) VALUES (?, ?)",
            (knowledge_id, blob),
        )
        conn.commit()
    finally:
        conn.close()


def delete_vector(knowledge_id: int) -> None:
    """删除知识点向量（知识被软删时调用）。"""
    conn = get_connection()
    try:
        conn.execute("DELETE FROM knowledge_vec WHERE knowledge_id = ?", (knowledge_id,))
        conn.commit()
    finally:
        conn.close()


def search_similar(
    query_embedding: list[float], top_k: int = SEARCH_DEFAULT_TOP_K
) -> list[dict]:
    """向量检索：返回 top_k 知识点（含 distance，越小越相似）。

    通过 JOIN knowledge 表过滤掉已软删的记录。
    """
    blob = _embedding_to_blob(query_embedding)
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT v.knowledge_id AS id, v.distance, k.content, k.subject, k.tags, k.created_at
            FROM knowledge_vec v
            JOIN knowledge k ON k.id = v.knowledge_id
            WHERE v.embedding MATCH ?
              AND k.deleted_at IS NULL
              AND v.k = ?
            ORDER BY v.distance
            """,
            (blob, top_k),
        ).fetchall()
    finally:
        conn.close()

    results = []
    for row in rows:
        results.append(
            {
                "id": row["id"],
                # sqlite-vec cosine distance ∈ [0,2]，转相似度：1 - distance
                "score": round(_distance_to_similarity(row["distance"]), 4),
                "content": row["content"],
                "subject": row["subject"],
                "tags": json.loads(row["tags"] or "[]"),
                "created_at": to_local_display(row["created_at"]),
            }
        )
    return results


def _distance_to_similarity(distance: float) -> float:
    """sqlite-vec 默认是 L2 距离；bge-m3 用余弦更合适，转成相似度分数 ∈ [0,1]。"""
    # sqlite-vec cosine = 1 - cosine_similarity，所以 similarity = 1 - distance
    # 用 clamp 保险
    return max(0.0, min(1.0, 1.0 - float(distance)))


def _embedding_to_blob(embedding: list[float]) -> bytes:
    """把 float list 转 sqlite-vec 需要的字节串（little-endian float32）。

    sqlite-vec 的 vec0 FLOAT[] 接受 JSON 文本或 float32 blob。用 blob 更快。
    """
    import struct

    return struct.pack(f"<{len(embedding)}f", *embedding)
