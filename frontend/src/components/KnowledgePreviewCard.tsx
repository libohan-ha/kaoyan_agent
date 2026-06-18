import { useMemo } from "react";
import { Button, Card, Form, Input, Select, Space, Tag } from "antd";
import { CheckOutlined, SaveOutlined } from "@ant-design/icons";
import type { KnowledgePreview, SubjectName } from "../types/api";

const subjects: SubjectName[] = ["政治", "英语", "数学", "计算机", "其他"];

interface Props {
  value: KnowledgePreview;
  loading?: boolean;
  onChange: (value: KnowledgePreview) => void;
  onConfirm: () => void;
}

export default function KnowledgePreviewCard({ value, loading, onChange, onConfirm }: Props) {
  const tagOptions = useMemo(
    () => value.tags.map((tag) => ({ label: tag, value: tag })),
    [value.tags]
  );

  return (
    <Card className="preview-card" title="知识点预览" size="small">
      <Form layout="vertical">
        <Form.Item label="内容">
          <Input.TextArea
            value={value.content}
            autoSize={{ minRows: 3, maxRows: 8 }}
            onChange={(event) => onChange({ ...value, content: event.target.value })}
          />
        </Form.Item>
        <div className="form-grid">
          <Form.Item label="学科">
            <Select
              value={value.subject}
              options={subjects.map((subject) => ({ label: subject, value: subject }))}
              onChange={(subject) => onChange({ ...value, subject })}
            />
          </Form.Item>
          <Form.Item label="标签">
            <Select
              mode="tags"
              value={value.tags}
              options={tagOptions}
              onChange={(tags) => onChange({ ...value, tags })}
              tagRender={({ label, closable, onClose }) => (
                <Tag closable={closable} onClose={onClose}>
                  {label}
                </Tag>
              )}
            />
          </Form.Item>
        </div>
        <Space>
          <Button
            type="primary"
            icon={loading ? <SaveOutlined /> : <CheckOutlined />}
            loading={loading}
            onClick={onConfirm}
          >
            确认保存
          </Button>
        </Space>
      </Form>
    </Card>
  );
}
