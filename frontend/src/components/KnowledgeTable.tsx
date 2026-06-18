import { Button, Popconfirm, Space, Table, Tag, Typography } from "antd";
import { DeleteOutlined, EditOutlined } from "@ant-design/icons";
import type { ColumnsType } from "antd/es/table";
import type { KnowledgeItem } from "../types/api";

interface Props {
  data: KnowledgeItem[];
  loading?: boolean;
  onEdit?: (item: KnowledgeItem) => void;
  onDelete?: (item: KnowledgeItem) => void;
}

export default function KnowledgeTable({ data, loading, onEdit, onDelete }: Props) {
  const columns: ColumnsType<KnowledgeItem> = [
    {
      title: "内容",
      dataIndex: "content",
      key: "content",
      render: (content: string) => (
        <Typography.Paragraph className="knowledge-content" ellipsis={{ rows: 3 }}>
          {content}
        </Typography.Paragraph>
      )
    },
    {
      title: "学科",
      dataIndex: "subject",
      width: 96,
      render: (subject: string) => <Tag color="blue">{subject}</Tag>
    },
    {
      title: "标签",
      dataIndex: "tags",
      width: 260,
      render: (tags: string[]) => (
        <Space size={[4, 4]} wrap>
          {tags.map((tag) => (
            <Tag key={tag}>{tag}</Tag>
          ))}
        </Space>
      )
    },
    {
      title: "分数",
      dataIndex: "score",
      width: 88,
      render: (score?: number) => (typeof score === "number" ? score.toFixed(4) : "-")
    },
    {
      title: "创建时间",
      dataIndex: "created_at",
      width: 172
    },
    {
      title: "操作",
      key: "action",
      width: 116,
      render: (_, item) => (
        <Space>
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
      )
    }
  ];

  return (
    <Table
      rowKey="id"
      columns={columns}
      dataSource={data}
      loading={loading}
      pagination={{ pageSize: 8, showSizeChanger: false }}
      scroll={{ x: 980 }}
    />
  );
}
