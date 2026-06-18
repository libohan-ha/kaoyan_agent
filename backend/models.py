"""Pydantic 请求 / 响应模型。"""
from pydantic import BaseModel, Field
from typing import Literal, Optional


# ===== 知识点 =====
class KnowledgeCreateRequest(BaseModel):
    content: str
    subject: Optional[str] = None
    tags: list[str] = Field(default_factory=list)
    auto_categorize: bool = True


class KnowledgePreviewRequest(BaseModel):
    content: str


class KnowledgeConfirmRequest(BaseModel):
    """确认保存（preview 流程的第二步）"""
    content: str
    subject: str
    tags: list[str]


class KnowledgeUpdateRequest(BaseModel):
    content: str
    subject: str
    tags: list[str]


class KnowledgeSearchRequest(BaseModel):
    query: Optional[str] = None
    q: Optional[str] = None
    top_k: int = Field(default=8, ge=1, le=50)
    subject: Optional[str] = None
    tag: Optional[str] = None
    date: Optional[str] = None
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    deleted: bool = False


class KnowledgeResponse(BaseModel):
    id: int
    content: str
    subject: str
    tags: list[str]
    created_at: str
    updated_at: str


class KnowledgePreviewResponse(BaseModel):
    content: str
    subject: str
    tags: list[str]


# ===== 对话 =====
class ChatRequest(BaseModel):
    message: str
    mode: Literal["save", "ask", "auto"] = "auto"
    history: list[dict] = Field(default_factory=list)
    session_id: Optional[int] = None


class ChatResponse(BaseModel):
    reply: str
    matched_knowledge: list[dict] = Field(default_factory=list)
    preview: Optional[dict] = None
    session_id: Optional[int] = None


# ===== 会话 =====
class SessionCreateRequest(BaseModel):
    title: Optional[str] = None


class SessionMessageCreateRequest(BaseModel):
    role: Literal["user", "assistant"]
    content: str
    matched_knowledge: list[dict] = Field(default_factory=list)
    preview: Optional[dict] = None
    thoughts: list[str] = Field(default_factory=list)


# ===== 通用 =====
class SubjectResponse(BaseModel):
    id: int
    name: str
    description: str
