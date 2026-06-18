"""知识点 CRUD + 检索路由。"""
from fastapi import APIRouter, HTTPException

from models import (
    KnowledgeCreateRequest,
    KnowledgePreviewRequest,
    KnowledgeConfirmRequest,
    KnowledgeUpdateRequest,
    KnowledgeSearchRequest,
    KnowledgePreviewResponse,
)
from services import knowledge_service
from services.ai_service import preview_knowledge_with_ai

router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])


@router.post("/preview")
def preview(req: KnowledgePreviewRequest) -> KnowledgePreviewResponse:
    """AI 分析内容，返回 {content, subject, tags} 预览（不保存）。"""
    result = preview_knowledge_with_ai(req.content)
    return {
        "content": result.get("content", req.content),
        "subject": result.get("subject", "其他"),
        "tags": result.get("tags", []),
    }


@router.post("/confirm")
def confirm(req: KnowledgeConfirmRequest):
    """确认保存预览的知识点（生成 embedding 并入向量库）。"""
    item = knowledge_service.create_knowledge(
        content=req.content, subject=req.subject, tags=req.tags, source="manual"
    )
    return item


@router.post("")
def create(req: KnowledgeCreateRequest):
    """外部 API 直接新建知识点（如 WeClaw skill 调用）。

    auto_categorize=True 时先 AI 分析学科/标签；False 时用传入的。
    """
    if req.auto_categorize and (not req.subject or req.subject == "其他"):
        preview_result = preview_knowledge_with_ai(req.content)
        subject = req.subject or preview_result.get("subject", "其他")
        tags = req.tags or preview_result.get("tags", [])
    else:
        subject = req.subject or "其他"
        tags = req.tags
    return knowledge_service.create_knowledge(
        content=req.content, subject=subject, tags=tags, source="api"
    )


@router.post("/search")
def search(req: KnowledgeSearchRequest):
    """语义检索 / 学科 / 日期 / 标签过滤。

    - 有 query：走向量检索
    - 无 query 但有 subject/date：走列表筛选
    """
    query = req.query or req.q
    if query:
        results = knowledge_service.search_by_query(query, top_k=req.top_k, subject=req.subject)
        return {"results": results, "query": query, "count": len(results)}

    items = knowledge_service.list_knowledge(
        subject=req.subject,
        tag=req.tag,
        date=req.date,
        date_from=req.date_from,
        date_to=req.date_to,
        deleted=req.deleted,
    )
    return {"results": items, "count": len(items)}


@router.get("")
def list_all(
    subject: str | None = None,
    tag: str | None = None,
    date: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    deleted: bool = False,
    limit: int = 100,
):
    items = knowledge_service.list_knowledge(
        subject=subject,
        tag=tag,
        date=date,
        date_from=date_from,
        date_to=date_to,
        deleted=deleted,
        limit=limit,
    )
    return {"results": items, "count": len(items)}


@router.get("/{kid}")
def get_one(kid: int):
    item = knowledge_service.get_knowledge_by_id(kid)
    if not item:
        raise HTTPException(status_code=404, detail=f"知识点 {kid} 不存在")
    return item


@router.put("/{kid}")
def update(kid: int, req: KnowledgeUpdateRequest):
    item = knowledge_service.update_knowledge(kid, req.content, req.subject, req.tags)
    if not item:
        raise HTTPException(status_code=404, detail=f"知识点 {kid} 不存在")
    return item


@router.delete("/{kid}")
def delete(kid: int):
    ok = knowledge_service.soft_delete(kid)
    if not ok:
        raise HTTPException(status_code=404, detail=f"知识点 {kid} 不存在或已删除")
    return {"ok": True, "id": kid}


@router.post("/{kid}/restore")
def restore(kid: int):
    ok = knowledge_service.restore(kid)
    if not ok:
        raise HTTPException(status_code=404, detail=f"知识点 {kid} 不存在或未删除")
    return knowledge_service.get_knowledge_by_id(kid)


@router.get("/tags/list")
def list_tags():
    return {"tags": knowledge_service.get_all_tags()}


@router.get("/subjects/list")
def list_subjects():
    return {"subjects": knowledge_service.get_subjects()}
