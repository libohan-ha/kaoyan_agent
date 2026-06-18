"""AI 服务：DeepSeek 对话 / 意图识别 / Function Calling 工具。

设计参考 自己skills 项目的 ai_service.py，把"经验"换成"知识点"，
学科体系改为考研五科（政治/英语/数学/计算机/其他）。
"""
import json
import re as _re
from openai import OpenAI
from openai import OpenAIError
from config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL, SEARCH_DEFAULT_TOP_K

# 客户端缓存（key 相同时复用）
_client_cache: dict[tuple, OpenAI] = {}

# ===== 学科（与 config.DEFAULT_SUBJECTS 对齐）=====
SUBJECTS = ["政治", "英语", "数学", "计算机", "其他"]

# ===== System Prompt（考研辅导 agent 人设）=====
SYSTEM_PROMPT = """你是用户的考研学习助手。你有以下工具可以调用，必须通过调用工具来完成操作，不能口头承诺。

【保存知识点】
当用户分享学到的知识点、题目、总结时，必须调用 preview_knowledge 分析内容，提取学科和标签。
考研学科共五个：政治、英语、数学、计算机、其他。判断学科举例：
- 涉及马原/毛中特/史纲/时政 → 政治
- 单词/阅读/长难句/翻译/作文 → 英语
- 高数/线代/概率论/微积分 → 数学
- 数据结构/操作系统/组成原理/计算机网络/算法 → 计算机
- 考研心态、时间管理、计划 → 其他

【检索知识点】
当用户提问、查知识点时，必须调用 search_knowledge 通过向量相似度检索相关知识点。

【按学科查看】
当用户想看某学科的知识点（如"看看我的数学笔记"），调用 search_by_subject。

【按日期查看】
当用户想查看某天记录的知识点（如"昨天学了什么"），调用 search_by_date。
当用户想看某段时间（如"最近一周的记录"），调用 search_by_date_range。

【今日复盘】
当用户说"今日复盘""复习一下""该复盘了"时，调用 get_yesterday_review，拉出昨天记录的知识点。

你了解的用户考研学科：
- 政治：马克思主义基本原理、毛中特、史纲、思修、时政
- 英语：英语一/二，单词、长难句、阅读、翻译、写作
- 数学：数学一/二/三，高数、线性代数、概率论
- 计算机：408 数据结构、计算机组成原理、操作系统、计算机网络
- 其他：考研心态、时间管理、计划、心得

重要原则：
- 必须调用工具来完成操作，绝对不能口头说"已保存""已记录"却不调用工具
- **关于保存**：你只能通过调用 preview_knowledge 生成预览卡片，最终保存动作是用户点击预览卡上的"确认"按钮。在用户确认之前，**绝对不要说"已保存""保存成功""已记下来"等任何宣称已保存的话**。应该把决定权交给用户："我帮你分析了这个知识点，请确认下面的预览卡"。
- **关于删除/编辑**：同理，未确认前不要宣称"已删除""已修改"。
- 优先使用用户自己记录的知识点来回答，而不是通用的考研知识
- 引用知识点时标注来源，让用户知道"这是你自己记的"
- 语气亲切，像同学/研友交流，可以适度鼓励
- 当调用 search_knowledge 时，如果用户明确说要几条（如"搜5条"），把数量填入 top_k；没说就用默认
- 用户追加消息（如"标签改成xxx""内容再加一句"）是对上次操作的补充，结合上下文直接调用对应工具
- 回复使用清晰的 Markdown，优先用标题、列表、加粗
- 不要输出 ```markdown 代码围栏包裹整段回复
- 绝对不要以文本形式输出工具调用，必须通过标准的 tool_calls 机制调用
"""

# ===== 工具定义（Function Calling）=====
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "preview_knowledge",
            "description": "分析知识点内容，返回学科分类和标签预览（不保存）",
            "parameters": {
                "type": "object",
                "properties": {
                    "content": {"type": "string", "description": "知识点内容"},
                    "subject": {
                        "type": "string",
                        "enum": SUBJECTS,
                        "description": "自动判断的考研学科",
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "提取的关键词/考点标签",
                    },
                },
                "required": ["content", "subject", "tags"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_knowledge",
            "description": "根据用户的问题或描述，通过向量相似度检索相关的考研知识点",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "用户的问题或场景描述"},
                    "top_k": {
                        "type": "integer",
                        "description": f"返回的知识点条数。用户明确指定时使用；未指定用默认 {SEARCH_DEFAULT_TOP_K}。正整数。",
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_by_subject",
            "description": "按学科查看用户记录的知识点。当用户想看某学科的笔记时调用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "subject": {
                        "type": "string",
                        "enum": SUBJECTS,
                        "description": "学科名",
                    },
                    "top_k": {"type": "integer", "description": "返回条数，默认 10"},
                },
                "required": ["subject"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_by_date",
            "description": "查询用户在某一天记录的知识点。当用户想看某天的记录时调用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "date": {
                        "type": "string",
                        "description": "查询日期 YYYY-MM-DD，如 2026-06-18。用户说6.18应转为2026-06-18。",
                    },
                },
                "required": ["date"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_by_date_range",
            "description": "查询指定日期范围内的知识点。当用户想看某段时间的记录时调用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "date_from": {"type": "string", "description": "起始日期 YYYY-MM-DD"},
                    "date_to": {"type": "string", "description": "结束日期 YYYY-MM-DD"},
                },
                "required": ["date_from", "date_to"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_yesterday_review",
            "description": "获取昨日复盘：拉出用户昨天记录的所有知识点，用于每日复习。",
            "parameters": {"type": "object", "properties": {}},
        },
    },
]


def _get_client() -> tuple[OpenAI, str]:
    """获取（带缓存的）DeepSeek OpenAI 兼容客户端 + 模型名。"""
    if not DEEPSEEK_API_KEY:
        raise RuntimeError("缺少 DEEPSEEK_API_KEY，无法调用 DeepSeek")
    cache_key = (DEEPSEEK_BASE_URL, DEEPSEEK_API_KEY, DEEPSEEK_MODEL)
    if cache_key not in _client_cache:
        _client_cache[cache_key] = OpenAI(
            api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL
        )
    return _client_cache[cache_key], DEEPSEEK_MODEL


# ===== 对话 + 工具调用 =====
def chat_with_tools(
    messages: list[dict],
    tool_choice: str = "auto",
    tools: list[dict] | None = None,
    timeout: int = 45,
) -> dict:
    client, model = _get_client()
    try:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            tools=tools or TOOLS,
            tool_choice=tool_choice,
            timeout=timeout,
        )
        return response
    except OpenAIError as exc:
        raise RuntimeError(f"AI 服务调用失败，请稍后再试：{exc}") from exc


def extract_tool_call(response) -> dict | None:
    """从响应中提取第一个工具调用。优先标准 tool_calls，其次解析文本里的 XML 工具调用（兜底）。"""
    choice = response.choices[0]
    message = choice.message

    if getattr(message, "tool_calls", None):
        tool_call = message.tool_calls[0]
        try:
            arguments = json.loads(tool_call.function.arguments or "{}")
        except json.JSONDecodeError as exc:
            raise RuntimeError("AI 工具参数不是有效 JSON") from exc
        return {
            "id": tool_call.id,
            "name": tool_call.function.name,
            "arguments": arguments or {},
            "raw_message": message,
        }

    text = message.content or ""
    fallback = _parse_text_tool_call(text)
    if fallback:
        fallback["raw_message"] = message
        return fallback
    return None


# 文本里的 XML 工具调用兜底解析（某些模型不返回标准 tool_calls）
_XML_TOOL_RE = _re.compile(
    r'\x3ctool_call\x3e\s*\x3cfunction=([^>]+)\x3e(.*?)\x3c/function\x3e\s*\x3c/tool_call\x3e',
    _re.DOTALL,
)
_XML_PARAM_RE = _re.compile(r'\x3cparameter=([^>]+)\x3e(.*?)\x3c/parameter\x3e', _re.DOTALL)
_TEXT_TOOL_BLOCK_RE = _re.compile(r'\x3ctool_call\x3e[\s\S]*?(?:\x3c/tool_call\x3e|$)', _re.IGNORECASE)
_TEXT_TOOL_TAG_RE = _re.compile(r'\x3c/?(?:tool_call|function|parameter)(?:=[^>]*)?\x3e', _re.IGNORECASE)


def strip_text_tool_calls(text: str) -> str:
    cleaned = _TEXT_TOOL_BLOCK_RE.sub("", text or "")
    cleaned = _TEXT_TOOL_TAG_RE.sub("", cleaned)
    return cleaned.strip()


def _parse_text_tool_call(text: str) -> dict | None:
    m = _XML_TOOL_RE.search(text)
    if not m:
        return None
    func_name = m.group(1).strip()
    body = m.group(2)
    params = {}
    for pm in _XML_PARAM_RE.finditer(body):
        key = pm.group(1).strip()
        val = pm.group(2).strip()
        try:
            val = json.loads(val)
        except Exception:
            pass
        params[key] = val
    return {
        "id": f"text-tool-{hash(text) & 0xFFFFFFFF:08x}",
        "name": func_name,
        "arguments": params,
    }


def build_tool_messages(tool_call: dict, tool_result: str) -> list[dict]:
    """构造工具调用回传给 LLM 的两条消息（assistant + tool）。"""
    raw_message = tool_call.get("raw_message")
    tool_call_id = tool_call["id"]
    sdk_tool_calls = []
    if raw_message is not None:
        sdk_tool_calls = [
            {
                "id": tc.id,
                "type": "function",
                "function": {
                    "name": tc.function.name,
                    "arguments": tc.function.arguments,
                },
            }
            for tc in (getattr(raw_message, "tool_calls", None) or [])
            if tc.id == tool_call_id
        ]

    if sdk_tool_calls:
        assistant_content = getattr(raw_message, "content", None) or ""
        assistant_tool_calls = sdk_tool_calls
    else:
        assistant_content = ""
        assistant_tool_calls = [
            {
                "id": tool_call_id,
                "type": "function",
                "function": {
                    "name": tool_call["name"],
                    "arguments": json.dumps(tool_call.get("arguments") or {}, ensure_ascii=False),
                },
            }
        ]

    assistant_msg = {
        "role": "assistant",
        "content": assistant_content,
        "tool_calls": assistant_tool_calls,
    }
    tool_msg = {"role": "tool", "tool_call_id": tool_call_id, "content": tool_result}
    return [assistant_msg, tool_msg]


# ===== 纯文本回复（含流式）=====
def generate_reply_stream(messages: list[dict]):
    client, model = _get_client()
    try:
        stream = client.chat.completions.create(
            model=model, messages=messages, stream=True, timeout=45
        )
        for chunk in stream:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta
            if delta and delta.content:
                yield delta.content
    except OpenAIError as exc:
        raise RuntimeError(f"AI 服务调用失败，请稍后再试：{exc}") from exc


# ===== 意图识别（LLM 兜底）=====
ALLOWED_INTENTS = {"save", "ask", "review", "normal_chat"}
ALLOWED_TOOL_NAMES = {tool["function"]["name"] for tool in TOOLS}


def extract_json_object(text: str) -> dict:
    cleaned = (text or "").strip()
    if cleaned.startswith("```"):
        cleaned = _re.sub(r"^```(?:json)?\s*", "", cleaned, flags=_re.IGNORECASE)
        cleaned = _re.sub(r"\s*```$", "", cleaned)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        match = _re.search(r"\{[\s\S]*\}", cleaned)
        if not match:
            return {}
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            return {}


def generate_intent(messages: list[dict], mode: str = "auto") -> dict:
    """LLM 兜底意图识别。返回 {intent, confidence, reason}。"""
    user_msg = ""
    for message in reversed(messages):
        if message.get("role") == "user":
            user_msg = message.get("content", "")
            break
    prompt = (
        "Classify the user's request for a 考研 (Chinese graduate entrance exam) study assistant. "
        "Return only JSON with keys: intent, confidence, reason. "
        "Allowed intents: save (record a new knowledge point), ask (query/explain), "
        "review (daily review of yesterday's notes), normal_chat. "
        f"Current UI mode: {mode}."
    )
    try:
        client, model = _get_client()
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": user_msg},
            ],
            timeout=20,
        )
        data = extract_json_object(response.choices[0].message.content or "")
        intent = data.get("intent") if data.get("intent") in ALLOWED_INTENTS else "normal_chat"
        try:
            confidence = float(data.get("confidence", 0))
        except (TypeError, ValueError):
            confidence = 0
        return {
            "intent": intent,
            "confidence": max(0, min(1, confidence)),
            "reason": str(data.get("reason") or ""),
        }
    except Exception:
        return {"intent": "normal_chat", "confidence": 0, "reason": ""}


# ===== 知识点预览（独立调用，给 /api/knowledge/preview 用）=====
def preview_knowledge_with_ai(content: str) -> dict:
    """让 AI 分析内容，返回 {content, subject, tags}。"""
    messages = [
        {
            "role": "system",
            "content": "你是用户的考研学习助手。请分析用户输入的知识点，判断考研学科（政治/英语/数学/计算机/其他）并提取考点标签。",
        },
        {"role": "user", "content": content},
    ]
    response = chat_with_tools(messages, tool_choice="required")
    tool_call = extract_tool_call(response)
    if tool_call and tool_call["name"] == "preview_knowledge":
        return tool_call["arguments"]
    return {"content": content, "subject": "其他", "tags": []}


# ===== 标题生成（会话用）=====
def generate_title(message: str) -> str:
    try:
        client, model = _get_client()
        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": "你是标题生成器。根据用户消息生成简短标题（不超过20字）。只输出标题。",
                },
                {"role": "user", "content": message},
            ],
            max_tokens=50,
        )
        title = response.choices[0].message.content.strip().replace("\n", " ")
        return title[:24] if title else message.strip()[:24]
    except Exception:
        return message.strip().replace("\n", " ")[:24]
