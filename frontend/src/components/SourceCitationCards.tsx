import { useState } from "react";
import { Button, Modal, Space, Tag, Typography } from "antd";
import { BookOutlined } from "@ant-design/icons";
import type { KnowledgeItem } from "../types/api";

interface Props {
  items: KnowledgeItem[];
}

const subjectColors: Record<string, string> = {
  政治: "#c1666b",
  英语: "#5b9aa0",
  数学: "#8a7290",
  计算机: "#5a8dee",
  其他: "#a08c6a"
};

function subjectColor(subject: string) {
  return subjectColors[subject] ?? "#64748b";
}

export default function SourceCitationCards({ items }: Props) {
  const [detail, setDetail] = useState<KnowledgeItem | null>(null);

  if (items.length === 0) return null;

  return (
    <div className="source-citation-list" aria-label="引用来源">
      <div className="source-citation-heading">
        <BookOutlined />
        <Typography.Text strong>引用了 {items.length} 条你的笔记</Typography.Text>
      </div>
      <div className="source-citation-grid">
        {items.map((item) => (
          <button
            key={item.id}
            type="button"
            className="source-citation-card"
            onClick={() => setDetail(item)}
          >
            <span className="source-citation-meta">
              <Tag color={subjectColor(item.subject)} style={{ color: "#fff", border: "none" }}>
                {item.subject}
              </Tag>
              <span>#{item.id}</span>
              {typeof item.score === "number" && <span>相关度 {item.score.toFixed(3)}</span>}
            </span>
            <span className="source-citation-content">{item.content}</span>
            <span className="source-citation-tags">
              {item.tags.slice(0, 4).map((tag) => (
                <Tag key={tag}>{tag}</Tag>
              ))}
            </span>
          </button>
        ))}
      </div>

      <Modal title="引用知识点" open={Boolean(detail)} footer={null} onCancel={() => setDetail(null)}>
        {detail && (
          <div className="knowledge-detail">
            <Typography.Paragraph className="knowledge-detail-content">
              {detail.content}
            </Typography.Paragraph>
            <Space size={[6, 6]} wrap>
              <Tag color={subjectColor(detail.subject)} style={{ color: "#fff", border: "none" }}>
                {detail.subject}
              </Tag>
              {detail.tags.map((tag) => (
                <Tag key={tag}>{tag}</Tag>
              ))}
              <Tag>#{detail.id}</Tag>
              {detail.created_at && <Tag>{detail.created_at}</Tag>}
            </Space>
            <div className="knowledge-detail-actions">
              <Button onClick={() => setDetail(null)}>关闭</Button>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
}
