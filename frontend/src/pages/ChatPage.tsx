import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import {
  App,
  Button,
  Card,
  Input,
  Space,
  Spin,
  Tag,
  Typography
} from "antd";
import { SendOutlined } from "@ant-design/icons";
import KnowledgePreviewCard from "../components/KnowledgePreviewCard";
import MarkdownContent from "../components/MarkdownContent";
import SourceCitationCards from "../components/SourceCitationCards";
import { confirmKnowledge, getSession, listSessions, streamChat } from "../services/api";
import {
  CHAT_NEW_SESSION_EVENT,
  CHAT_SESSIONS_UPDATED_EVENT,
  LAST_SESSION_KEY
} from "../sessionState";
import type { ChatMessage, ChatSession, KnowledgePreview, StoredChatMessage } from "../types/api";

const starterPrompts: Array<{ title: string; description: string; prompt: string }> = [
  {
    title: "记录一个知识点",
    description: "AI 自动分类、打标签，确认后入库",
    prompt: "今天学了 "
  },
  {
    title: "问问我的笔记",
    description: "优先检索你自己记录过的内容",
    prompt: "根据我的笔记，"
  },
  {
    title: "今日复盘",
    description: "看看今天新增的知识点",
    prompt: "今日复盘"
  },
  {
    title: "最近学了什么",
    description: "回顾最近一段时间的记录",
    prompt: "最近一周我学了什么？"
  }
];

function nextId() {
  return `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function mapStoredMessage(item: StoredChatMessage): ChatMessage {
  return {
    id: `stored-${item.id}`,
    role: item.role,
    content: item.content,
    matched: item.matched_knowledge,
    preview: item.preview ?? undefined,
    thoughts: item.thoughts
  };
}

export default function ChatPage() {
  const { message } = App.useApp();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [sessionTitle, setSessionTitle] = useState("新对话");
  const [savingPreviewId, setSavingPreviewId] = useState<string | null>(null);
  const sessionIdRef = useRef<number | undefined>();
  const initialRestoreDoneRef = useRef(false);

  const canSend = useMemo(() => input.trim().length > 0 && !loading, [input, loading]);
  const sessionIdFromUrl = useMemo(() => {
    const raw = searchParams.get("session");
    const value = Number(raw);
    return Number.isInteger(value) && value > 0 ? value : undefined;
  }, [searchParams]);
  const isNewChatRequest = searchParams.has("new");

  const updateAssistant = (id: string, patch: Partial<ChatMessage>) => {
    setMessages((items) =>
      items.map((item) => (item.id === id ? { ...item, ...patch } : item))
    );
  };

  const resetChatState = useCallback(() => {
    sessionIdRef.current = undefined;
    window.localStorage.removeItem(LAST_SESSION_KEY);
    setSessionTitle("新对话");
    setMessages([]);
    setInput("");
    setSavingPreviewId(null);
    setHistoryLoading(false);
  }, []);

  const applySession = useCallback(
    (result: { session: ChatSession; messages: StoredChatMessage[] }) => {
      sessionIdRef.current = result.session.id;
      window.localStorage.setItem(LAST_SESSION_KEY, String(result.session.id));
      setSessionTitle(result.session.title || "新对话");
      setMessages(result.messages.map(mapStoredMessage));
    },
    []
  );

  const loadSession = useCallback(async (sessionId: number) => {
    const result = await getSession(sessionId);
    applySession(result);
    return result;
  }, [applySession]);

  useEffect(() => {
    if (!sessionIdFromUrl) return;
    let cancelled = false;
    const restoreFromUrl = async () => {
      setHistoryLoading(true);
      try {
        const result = await getSession(sessionIdFromUrl);
        if (cancelled) return;
        applySession(result);
      } catch {
        if (!cancelled) {
          window.localStorage.removeItem(LAST_SESSION_KEY);
          message.error("加载会话失败");
        }
      } finally {
        if (!cancelled) setHistoryLoading(false);
      }
    };

    void restoreFromUrl();
    return () => {
      cancelled = true;
    };
  }, [applySession, message, sessionIdFromUrl]);

  useEffect(() => {
    if (isNewChatRequest) resetChatState();
  }, [isNewChatRequest, resetChatState]);

  useEffect(() => {
    window.addEventListener(CHAT_NEW_SESSION_EVENT, resetChatState);
    return () => {
      window.removeEventListener(CHAT_NEW_SESSION_EVENT, resetChatState);
    };
  }, [resetChatState]);

  useEffect(() => {
    if (initialRestoreDoneRef.current) return;
    initialRestoreDoneRef.current = true;
    if (sessionIdFromUrl || isNewChatRequest) return;

    let cancelled = false;
    const restore = async () => {
      setHistoryLoading(true);
      try {
        const stored = Number(window.localStorage.getItem(LAST_SESSION_KEY));
        if (stored) {
          const result = await getSession(stored);
          if (cancelled) return;
          applySession(result);
          navigate(`/chat?session=${result.session.id}`, { replace: true });
          return;
        }

        const result = await listSessions();
        if (cancelled) return;
        const latest = result.sessions[0];
        if (latest) {
          const session = await loadSession(latest.id);
          if (!cancelled) navigate(`/chat?session=${session.session.id}`, { replace: true });
        }
      } catch {
        window.localStorage.removeItem(LAST_SESSION_KEY);
      } finally {
        if (!cancelled) setHistoryLoading(false);
      }
    };

    void restore();
    return () => {
      cancelled = true;
    };
  }, [applySession, isNewChatRequest, loadSession, navigate, sessionIdFromUrl]);

  const useStarterPrompt = (prompt: (typeof starterPrompts)[number]) => {
    setInput(prompt.prompt);
  };

  const send = async () => {
    const text = input.trim();
    if (!text || loading) return;
    const userMessage: ChatMessage = { id: nextId(), role: "user", content: text };
    const assistantId = nextId();
    const assistantMessage: ChatMessage = { id: assistantId, role: "assistant", content: "" };

    setMessages((items) => [...items, userMessage, assistantMessage]);
    setInput("");
    setLoading(true);

    const thoughts: string[] = [];
    let content = "";
    let preview: KnowledgePreview | undefined;

    try {
      const sessionId = await streamChat(
        { message: text, mode: "auto", session_id: sessionIdRef.current },
        (event) => {
          if (event.type === "token") {
            content += event.content;
            updateAssistant(assistantId, { content });
          }
          if (event.type === "reply") {
            content = event.content;
            updateAssistant(assistantId, { content });
          }
          if (event.type === "thought") {
            thoughts.push(event.content);
            updateAssistant(assistantId, { thoughts: [...thoughts] });
          }
          if (event.type === "preview") {
            preview = event.data;
            updateAssistant(assistantId, { preview });
          }
          if (event.type === "matched") {
            updateAssistant(assistantId, { matched: event.data });
          }
          if (event.type === "error") {
            content = event.content;
            updateAssistant(assistantId, { content, error: true });
          }
        }
      );
      sessionIdRef.current = sessionId;
      if (sessionId) {
        window.localStorage.setItem(LAST_SESSION_KEY, String(sessionId));
        if (sessionTitle === "新对话") setSessionTitle(text.slice(0, 24));
        navigate(`/chat?session=${sessionId}`, { replace: true });
        window.dispatchEvent(new Event(CHAT_SESSIONS_UPDATED_EVENT));
      }
    } catch (error) {
      updateAssistant(assistantId, {
        content: error instanceof Error ? error.message : "请求失败",
        error: true
      });
    } finally {
      setLoading(false);
    }
  };

  const confirmPreview = async (id: string, preview: KnowledgePreview) => {
    if (!preview.content.trim()) {
      message.warning("内容不能为空");
      return;
    }
    setSavingPreviewId(id);
    try {
      const item = await confirmKnowledge(preview);
      message.success(`已保存 #${item.id}`);
      updateAssistant(id, { preview: undefined });
    } catch (error) {
      message.error(error instanceof Error ? error.message : "保存失败");
    } finally {
      setSavingPreviewId(null);
    }
  };

  return (
    <div className="page-grid chat-page">
      <section className="chat-toolbar">
        <div>
          <Typography.Text strong>{sessionTitle}</Typography.Text>
          <Typography.Text type="secondary" className="chat-session-meta">
            {sessionIdRef.current ? `会话 #${sessionIdRef.current}` : "尚未开始"}
          </Typography.Text>
        </div>
      </section>

      <section className="chat-thread">
        {historyLoading ? (
          <div className="empty-state">
            <Spin />
          </div>
        ) : messages.length === 0 ? (
          <div className="chat-hero">
            <div className="chat-hero-copy">
              <Typography.Title level={1}>今天学了什么？</Typography.Title>
              <Typography.Paragraph>
                随手记一句，AI 帮你分类；忘了就问，它会优先翻你自己的知识库。
              </Typography.Paragraph>
            </div>
            <div className="starter-prompt-grid">
              {starterPrompts.map((prompt) => (
                <button
                  key={prompt.title}
                  type="button"
                  className="starter-prompt-card"
                  onClick={() => useStarterPrompt(prompt)}
                >
                  <strong>{prompt.title}</strong>
                  <span>{prompt.description}</span>
                </button>
              ))}
            </div>
          </div>
        ) : (
          messages.map((item) => (
            <div key={item.id} className={`message-row ${item.role}`}>
              <Card className={`message-card ${item.error ? "error" : ""}`} size="small">
                <Typography.Text className="message-role">
                  {item.role === "user" ? "你" : "Agent"}
                </Typography.Text>
                {item.content ? (
                  <MarkdownContent content={item.content} className="message-content chat-markdown" />
                ) : loading && item.role === "assistant" ? (
                  <div className="message-content">
                    <Spin size="small" />
                  </div>
                ) : null}
                {item.thoughts && item.thoughts.length > 0 && (
                  <Space size={[4, 4]} wrap className="thoughts-line">
                    {item.thoughts.map((thought) => (
                      <Tag key={thought}>{thought}</Tag>
                    ))}
                  </Space>
                )}
                {item.matched && item.matched.length > 0 && (
                  <SourceCitationCards items={item.matched} />
                )}
                {item.preview && (
                  <KnowledgePreviewCard
                    value={item.preview}
                    loading={savingPreviewId === item.id}
                    onChange={(value) => updateAssistant(item.id, { preview: value })}
                    onConfirm={() => confirmPreview(item.id, item.preview!)}
                  />
                )}
              </Card>
            </div>
          ))
        )}
      </section>

      <section className="composer-panel">
        <Input.TextArea
          value={input}
          autoSize={{ minRows: 2, maxRows: 5 }}
          placeholder="输入知识点或问题"
          onChange={(event) => setInput(event.target.value)}
          onPressEnter={(event) => {
            if (!event.shiftKey) {
              event.preventDefault();
              void send();
            }
          }}
        />
        <Button type="primary" icon={<SendOutlined />} loading={loading} disabled={!canSend} onClick={send}>
          发送
        </Button>
      </section>
    </div>
  );
}
