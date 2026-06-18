"""对话编排路由：意图识别 → 工具调用 → SSE 流式回复。

核心循环（参考 自己skills 的 agent.py）：
1. 关键词正则快速判断意图 + tool_choice（省钱）
2. 调 DeepSeek 带 tools → 提取 tool_call
3. 分发到对应工具处理函数（search/preview/...）
4. 预览类工具（preview/edit/delete）→ 直接返回，等用户确认
5. 检索类工具 → 把结果塞回 messages → 继续循环让 LLM 生成回答
6. 无工具调用 → 纯文本流式生成

全程用 SSE 推送进度（thought/reply/token/matched/preview/done）。
"""
import json as _json
import re
from datetime import datetime

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from config import SEARCH_DEFAULT_TOP_K
from models import ChatRequest
from services import knowledge_service, session_service
from services.ai_service import (
    SYSTEM_PROMPT,
    TOOLS,
    build_tool_messages,
    chat_with_tools,
    extract_tool_call,
    generate_reply_stream,
    strip_text_tool_calls,
)

router = APIRouter(prefix="/api/agent", tags=["agent"])

# ===== 关键词正则（快速意图判断）=====
SAVE_KEYWORDS = re.compile(r"(保存|记录|记一下|记下来|存一下|学到了|今天学了|学了一道|记一道|背了|刷了)")
SEARCH_KEYWORDS = re.compile(r"(搜索|搜一下|查一下|找一下|找找|检索|命中|哪条|哪道|相关知识点|怎么|什么是|什么叫做|解释一下|讲讲)")
REVIEW_KEYWORDS = re.compile(r"(复盘|复习|回顾|昨日|昨天.*学|今日.*复盘)")
EDIT_KEYWORDS = re.compile(r"(编辑|修改|改一下|更新|改成|改为|把.*改)")
DELETE_KEYWORDS = re.compile(r"(删除|删掉|去掉|移除)")
QUESTION_RE = re.compile(r"[?？]")
GREETING_RE = re.compile(r"^(你好|hi|hello|嗨|在吗|测试|试试)\b", re.IGNORECASE)

# 模型在自由文本里幻觉"已操作"的短语（输出层守门）
HALLUCINATED_ACTION_RE = re.compile(
    r"(已保存|已记录|已记下|保存成功|记录成功|已修改|已编辑|修改成功|编辑成功|已更新|更新成功|已删除|删除成功)"
)

MAX_TOOL_ROUNDS = 4
SEARCH_MAX_TOP_K = 30

SEARCH_TOOL_NAMES = {"search_knowledge", "search_by_subject", "search_by_date", "search_by_date_range"}
SEARCH_TOOLS = [t for t in TOOLS if t["function"]["name"] in SEARCH_TOOL_NAMES]


def _extract_requested_top_k(text: str) -> int | None:
    """从文本里提取"搜5条""找3个"等数量。"""
    m = re.search(r"(\d{1,2})\s*(?:条|个|篇|则|项|道)", text or "")
    if m:
        return int(m.group(1))
    return None


def _resolve_top_k(raw_value, user_message: str = "") -> int:
    requested = _extract_requested_top_k(user_message)
    if requested:
        return max(1, min(requested, SEARCH_MAX_TOP_K))
    try:
        top_k = int(raw_value)
    except (TypeError, ValueError):
        top_k = SEARCH_DEFAULT_TOP_K
    top_k = max(top_k, SEARCH_DEFAULT_TOP_K)
    return max(1, min(top_k, SEARCH_MAX_TOP_K))


def _clean_message(text: str) -> str:
    """清洗用户消息（去掉多余空白）。"""
    t = (text or "").strip()
    t = re.sub(r"\n{2,}", "\n", t)
    return t


def _build_chat_messages(trusted_history, clean_msg, mode_instruction, now):
    system_content = SYSTEM_PROMPT + f"\n\n当前时间：{now}" + (
        f"\n\n{mode_instruction}" if mode_instruction else ""
    )
    messages = [{"role": "system", "content": system_content}]
    for h in trusted_history:
        role = h.get("role")
        content = h.get("content")
        if role in {"user", "assistant"} and isinstance(content, str) and content:
            messages.append({"role": role, "content": role == "user" and _clean_message(content) or content})
    messages.append({"role": "user", "content": clean_msg})
    return messages


def _record_event(events, tool, summary):
    events.append({"tool": tool, "summary": summary})


def _handle_tool_call(tool_call, messages, events, user_message=""):
    """处理一次工具调用，返回 dict（type 决定后续流程）。"""
    tool_name = tool_call["name"]
    args = tool_call["arguments"] or {}
    events = events if events is not None else []

    # ---- 保存预览 ----
    if tool_name == "preview_knowledge":
        preview = {
            "content": args.get("content", ""),
            "subject": args.get("subject", "其他"),
            "tags": args.get("tags", []),
        }
        _record_event(events, tool_name, f"生成保存预览，学科「{preview['subject']}」，{len(preview['tags'])} 个标签。")
        return {"type": "preview", "preview": preview}

    # ---- 语义检索 ----
    if tool_name == "search_knowledge":
        top_k = _resolve_top_k(args.get("top_k"), user_message)
        query = knowledge_service.clean_search_query(args.get("query", ""))
        results = knowledge_service.search_by_query(query, top_k=top_k)
        _record_event(events, tool_name, f"检索知识库，命中 {len(results)} 条相关知识点。")
        if not results:
            return {"type": "text", "reply": "在你的知识库里没找到相关知识点。要不要先记一条？", "matched": []}
        lines = [
            f"{i}. ID:{r['id']} 『{r['content']}』—— {r['subject']} (相似度: {r.get('score', 'N/A')})"
            for i, r in enumerate(results, 1)
        ]
        context = f"用户的知识库中有以下 {len(results)} 条相关知识点：\n" + "\n".join(lines)
        messages.extend(build_tool_messages(tool_call, context))
        matched = [
            {"id": r["id"], "content": r["content"], "subject": r["subject"],
             "score": r.get("score"), "tags": r.get("tags", []), "created_at": r.get("created_at")}
            for r in results
        ]
        return {"type": "continue", "matched": matched}

    # ---- 按学科 ----
    if tool_name == "search_by_subject":
        subject = args.get("subject", "其他")
        limit = _resolve_top_k(args.get("top_k"), user_message) or 10
        results = knowledge_service.get_by_subject(subject, limit=limit)
        _record_event(events, tool_name, f"按学科「{subject}」查询，找到 {len(results)} 条。")
        if not results:
            return {"type": "text", "reply": f"「{subject}」学科下还没有知识点记录。", "matched": []}
        lines = [f"{i}. ID:{r['id']} 『{r['content']}』({r['created_at']})" for i, r in enumerate(results, 1)]
        context = f"用户「{subject}」学科下共 {len(results)} 条知识点：\n" + "\n".join(lines)
        messages.extend(build_tool_messages(tool_call, context))
        matched = [{"id": r["id"], "content": r["content"], "subject": r["subject"],
                    "tags": r.get("tags", []), "created_at": r.get("created_at")} for r in results]
        return {"type": "continue", "matched": matched}

    # ---- 按日期 ----
    if tool_name == "search_by_date":
        date_str = args.get("date", "")
        results = knowledge_service.get_by_date(date_str)
        _record_event(events, tool_name, f"按日期 {date_str} 查询，找到 {len(results)} 条。")
        if not results:
            return {"type": "text", "reply": f"{date_str} 没有知识点记录。", "matched": []}
        lines = [f"{i}. ID:{r['id']} 『{r['content']}』—— {r['subject']} ({r['created_at']})" for i, r in enumerate(results, 1)]
        context = f"用户在 {date_str} 共记录 {len(results)} 条知识点：\n" + "\n".join(lines)
        messages.extend(build_tool_messages(tool_call, context))
        matched = [{"id": r["id"], "content": r["content"], "subject": r["subject"],
                    "created_at": r.get("created_at")} for r in results]
        return {"type": "continue", "matched": matched}

    # ---- 按日期范围 ----
    if tool_name == "search_by_date_range":
        date_from, date_to = args.get("date_from", ""), args.get("date_to", "")
        results = knowledge_service.get_by_date_range(date_from, date_to)
        _record_event(events, tool_name, f"按范围 {date_from}~{date_to} 查询，找到 {len(results)} 条。")
        if not results:
            return {"type": "text", "reply": f"{date_from} 到 {date_to} 没有知识点记录。", "matched": []}
        lines = [f"{i}. ID:{r['id']} 『{r['content']}』—— {r['subject']} ({r['created_at']})" for i, r in enumerate(results, 1)]
        context = f"用户 {date_from}~{date_to} 共记录 {len(results)} 条知识点：\n" + "\n".join(lines)
        messages.extend(build_tool_messages(tool_call, context))
        matched = [{"id": r["id"], "content": r["content"], "subject": r["subject"],
                    "created_at": r.get("created_at")} for r in results]
        return {"type": "continue", "matched": matched}

    # ---- 昨日复盘 ----
    if tool_name == "get_yesterday_review":
        results = knowledge_service.get_yesterday_knowledge()
        _record_event(events, tool_name, f"拉取昨日记录 {len(results)} 条。")
        if not results:
            return {"type": "text", "reply": "昨天没有新的知识点记录哦，今天加油！", "matched": []}
        from services.review_service import build_review_content

        _, content = build_review_content(results)
        context = "用户昨日的知识点记录如下：\n" + content
        messages.extend(build_tool_messages(tool_call, context))
        matched = [{"id": r["id"], "content": r["content"], "subject": r["subject"],
                    "created_at": r.get("created_at")} for r in results]
        return {"type": "continue", "matched": matched}

    return {"type": "unknown"}


@router.post("/chat")
def chat(req: ChatRequest):
    try:
        session = session_service.get_or_create_session(req.session_id, req.message)
        session_id = session["id"]
        trusted_history = session_service.get_trusted_chat_history(session_id)
        session_service.update_session_title_if_default(session_id, req.message)
        session_service.add_message(session_id, "user", req.message)

        clean_msg = _clean_message(req.message)

        if req.mode == "save":
            mode_instruction = "用户当前处于【保存知识点】模式，请调用 preview_knowledge 提取学科和标签。"
        elif req.mode == "ask":
            mode_instruction = "用户当前处于【提问】模式，请调用 search_knowledge 检索相关知识点并回答。"
        else:
            mode_instruction = ""

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        messages = _build_chat_messages(trusted_history, clean_msg, mode_instruction, now)

        def _full_gen():
            all_matched = []
            execution_events = []
            process_trace = []

            def _emit_process_step(content):
                content = (content or "").strip()
                if not content:
                    return
                process_trace.append(content)
                yield _sse({"type": "thought_start"})
                yield _sse({"type": "thought", "content": content})
                yield _sse({"type": "thought_end"})

            def _emit_new_events(start_index):
                for ev in execution_events[start_index:]:
                    yield from _emit_process_step(ev.get("summary", ""))

            try:
                yield from _emit_process_step("正在匹配合适的处理方式。")

                for _ in range(MAX_TOOL_ROUNDS):
                    # 快速意图判断（关键词优先，省钱）
                    search_only = (
                        req.mode == "ask" or SEARCH_KEYWORDS.search(clean_msg)
                    ) and not (EDIT_KEYWORDS.search(clean_msg) or DELETE_KEYWORDS.search(clean_msg) or SAVE_KEYWORDS.search(clean_msg))
                    # "知识点陈述"启发式：长内容、非问句、非问候、无动作词 → 视为想保存
                    looks_like_statement = (
                        len(clean_msg) >= 8
                        and not QUESTION_RE.search(clean_msg)
                        and not GREETING_RE.search(clean_msg)
                        and not SEARCH_KEYWORDS.search(clean_msg)
                        and not EDIT_KEYWORDS.search(clean_msg)
                        and not DELETE_KEYWORDS.search(clean_msg)
                    )
                    force_tool = (
                        req.mode in {"ask", "save"}
                        or bool(SEARCH_KEYWORDS.search(clean_msg))
                        or bool(REVIEW_KEYWORDS.search(clean_msg))
                        or bool(SAVE_KEYWORDS.search(clean_msg))
                        or looks_like_statement
                    )
                    response = chat_with_tools(
                        messages,
                        tool_choice="required" if force_tool else "auto",
                        tools=SEARCH_TOOLS if search_only else None,
                    )
                    tool_call = extract_tool_call(response)

                    if not tool_call and SAVE_KEYWORDS.search(clean_msg):
                        # 明确说了"记一下"但模型没调工具，强制再试
                        response = chat_with_tools(messages, tool_choice="required")
                        tool_call = extract_tool_call(response)
                    if not tool_call and SEARCH_KEYWORDS.search(clean_msg):
                        response = chat_with_tools(messages, tool_choice="required", tools=SEARCH_TOOLS)
                        tool_call = extract_tool_call(response)

                    if not tool_call:
                        break

                    event_start = len(execution_events)
                    result = _handle_tool_call(
                        tool_call, messages, execution_events, user_message=clean_msg
                    )
                    yield from _emit_new_events(event_start)

                    if result["type"] == "preview":
                        reply = "我帮你分析了这个知识点："
                        session_service.add_message(
                            session_id, "assistant", reply, preview=result["preview"], thoughts=process_trace
                        )
                        yield _sse({"type": "reply", "content": reply})
                        yield _sse({"type": "preview", "data": result["preview"]})
                        yield _sse({"type": "done", "session_id": session_id})
                        return

                    if result["type"] == "text":
                        reply = result["reply"]
                        matched = result.get("matched") or []
                        session_service.add_message(
                            session_id, "assistant", reply, matched_knowledge=matched, thoughts=process_trace
                        )
                        yield _sse({"type": "reply", "content": reply})
                        if matched:
                            yield _sse({"type": "matched", "data": matched})
                        yield _sse({"type": "done", "session_id": session_id})
                        return

                    if result["type"] == "continue":
                        if "matched" in result:
                            all_matched = result["matched"]
                        # 检索后继续循环让 LLM 生成回答
                        continue

                    break

                # 走纯文本流式生成
                full_reply = []
                yield from _emit_process_step("正在生成回复。")
                for chunk in generate_reply_stream(messages):
                    full_reply.append(chunk)
                    yield _sse({"type": "token", "content": chunk})
                reply_text = "".join(full_reply)
                clean_reply = strip_text_tool_calls(reply_text)
                if clean_reply != reply_text:
                    reply_text = clean_reply
                    yield _sse({"type": "reply", "content": reply_text})
                # 守门：自由文本里幻觉"已保存"等 → 纠正
                if HALLUCINATED_ACTION_RE.search(reply_text or ""):
                    reply_text = (
                        "（提示：上面这个知识点我还没真正保存。想记录的话回复\"保存\"，"
                        "我会生成预览卡让你确认。）\n\n" + (reply_text or "")
                    )
                    yield _sse({"type": "reply", "content": reply_text})
                session_service.add_message(
                    session_id, "assistant", reply_text, matched_knowledge=all_matched, thoughts=process_trace
                )
                if all_matched:
                    yield _sse({"type": "matched", "data": all_matched})
                yield _sse({"type": "done", "session_id": session_id})
            except Exception as exc:
                error_msg = f"请求失败：{exc}"
                session_service.add_message(session_id, "assistant", error_msg, thoughts=process_trace)
                yield _sse({"type": "error", "content": error_msg})
                yield _sse({"type": "done", "session_id": session_id})

        return _sse_response(_full_gen())
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Agent chat failed: {type(exc).__name__}: {exc}") from exc


def _sse(data: dict) -> str:
    return f"data: {_json.dumps(data, ensure_ascii=False)}\n\n"


def _sse_response(gen):
    return StreamingResponse(
        gen,
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no", "Connection": "keep-alive"},
    )
