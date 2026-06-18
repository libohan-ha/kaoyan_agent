import { useMemo, useRef, useState } from "react";
import {
  App,
  Button,
  Card,
  Empty,
  Input,
  Segmented,
  Space,
  Spin,
  Tag,
  Typography
} from "antd";
import { SendOutlined } from "@ant-design/icons";
import KnowledgePreviewCard from "../components/KnowledgePreviewCard";
import { confirmKnowledge, streamChat } from "../services/api";
import type { ChatMessage, ChatMode, KnowledgePreview } from "../types/api";

const modeOptions = [
  { label: "自动", value: "auto" },
  { label: "保存", value: "save" },
  { label: "提问", value: "ask" }
];

function nextId() {
  return `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

export default function ChatPage() {
  const { message } = App.useApp();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [mode, setMode] = useState<ChatMode>("auto");
  const [loading, setLoading] = useState(false);
  const [savingPreviewId, setSavingPreviewId] = useState<string | null>(null);
  const sessionIdRef = useRef<number | undefined>();

  const canSend = useMemo(() => input.trim().length > 0 && !loading, [input, loading]);

  const updateAssistant = (id: string, patch: Partial<ChatMessage>) => {
    setMessages((items) =>
      items.map((item) => (item.id === id ? { ...item, ...patch } : item))
    );
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
        { message: text, mode, session_id: sessionIdRef.current },
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
      <section className="chat-thread">
        {messages.length === 0 ? (
          <Empty description="暂无对话" className="empty-state" />
        ) : (
          messages.map((item) => (
            <div key={item.id} className={`message-row ${item.role}`}>
              <Card className={`message-card ${item.error ? "error" : ""}`} size="small">
                <Typography.Text className="message-role">
                  {item.role === "user" ? "你" : "Agent"}
                </Typography.Text>
                <Typography.Paragraph className="message-content">
                  {item.content || (loading && item.role === "assistant" ? <Spin size="small" /> : "")}
                </Typography.Paragraph>
                {item.thoughts && item.thoughts.length > 0 && (
                  <Space size={[4, 4]} wrap className="thoughts-line">
                    {item.thoughts.map((thought) => (
                      <Tag key={thought}>{thought}</Tag>
                    ))}
                  </Space>
                )}
                {item.matched && item.matched.length > 0 && (
                  <div className="matched-list">
                    {item.matched.map((match) => (
                      <div key={match.id} className="matched-item">
                        <Tag color="geekblue">#{match.id}</Tag>
                        <span>{match.content}</span>
                      </div>
                    ))}
                  </div>
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
        <Segmented
          value={mode}
          options={modeOptions}
          onChange={(value) => setMode(value as ChatMode)}
        />
        <Input.TextArea
          value={input}
          autoSize={{ minRows: 4, maxRows: 8 }}
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
