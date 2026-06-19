import { useState } from "react";
import { Button, Empty, Modal, Popconfirm, Space, Spin, Tag, Typography } from "antd";
import { DeleteOutlined, EditOutlined, FileTextOutlined } from "@ant-design/icons";
import type { KnowledgeItem } from "../types/api";

interface Props {
  data: KnowledgeItem[];
  loading?: boolean;
  onEdit?: (item: KnowledgeItem) => void;
  onDelete?: (item: KnowledgeItem) => void;
}

const subjectColors: Record<string, string> = {
  政治: "#c1666b",
  英语: "#5b9aa0",
  数学: "#8a7290",
  计算机: "#5a8dee",
  其他: "#a08c6a"
};

export default function KnowledgeTable({ data, loading, onEdit, onDelete }: Props) {
  const [detailItem, setDetailItem] = useState<KnowledgeItem | null>(null);

  const editFromDetail = () => {
    if (!detailItem) return;
    onEdit?.(detailItem);
    setDetailItem(null);
  };

  const subjectColor = (subject: string) => subjectColors[subject] ?? "#a08c6a";

  return (
    <>
      <div className="knowledge-card-list" aria-busy={loading}>
        {loading ? (
          <div className="knowledge-card-loading">
            <Spin />
          </div>
        ) : data.length === 0 ? (
          <Empty description="暂无知识点" />
        ) : (
          data.map((item) => (
            <article key={item.id} className="knowledge-card">
              <button
                type="button"
                className="knowledge-card-main"
                aria-label="展开知识点详情"
                onClick={() => setDetailItem(item)}
              >
                <span className="knowledge-card-icon">
                  <FileTextOutlined />
                </span>
                <span className="knowledge-card-body">
                  <span className="knowledge-card-topline">
                    <Tag color={subjectColor(item.subject)} style={{ color: "#fff", border: "none" }}>
                      {item.subject}
                    </Tag>
                    <span>#{item.id}</span>
                    <span>{item.created_at}</span>
                    {typeof item.score === "number" && <span>相关度 {item.score.toFixed(3)}</span>}
                  </span>
                  <Typography.Paragraph className="knowledge-card-content" ellipsis={{ rows: 3 }}>
                    {item.content}
                  </Typography.Paragraph>
                  <span className="knowledge-card-tags">
                    {item.tags.map((tag) => (
                      <Tag key={tag}>{tag}</Tag>
                    ))}
                  </span>
                </span>
              </button>
              <Space className="knowledge-card-actions">
                <Button
                  size="small"
                  icon={<EditOutlined />}
                  aria-label="编辑"
                  onClick={() => onEdit?.(item)}
                />
                <Popconfirm
                  title="删除这条知识点？"
                  okText="删除"
                  cancelText="取消"
                  onConfirm={() => onDelete?.(item)}
                >
                  <Button size="small" danger icon={<DeleteOutlined />} aria-label="删除" />
                </Popconfirm>
              </Space>
            </article>
          ))
        )}
      </div>
      <Modal
        title="详情"
        open={Boolean(detailItem)}
        onCancel={() => setDetailItem(null)}
        footer={null}
      >
        {detailItem && (
          <div aria-label="知识点详情" className="knowledge-detail">
            <Typography.Paragraph className="knowledge-detail-content">
              {detailItem.content}
            </Typography.Paragraph>
            <Space size={[6, 6]} wrap>
              <Tag color={subjectColor(detailItem.subject)} style={{ color: "#fff", border: "none" }}>
                {detailItem.subject}
              </Tag>
              {detailItem.tags.map((tag) => (
                <Tag key={tag}>{tag}</Tag>
              ))}
            </Space>
            <div className="knowledge-detail-actions">
              <Button onClick={() => setDetailItem(null)}>关闭</Button>
              <Button
                type="primary"
                icon={<EditOutlined />}
                aria-label="编辑"
                onClick={editFromDetail}
              >
                编辑
              </Button>
            </div>
          </div>
        )}
      </Modal>
    </>
  );
}
