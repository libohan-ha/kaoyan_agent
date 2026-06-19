import { useEffect, useMemo, useState } from "react";
import {
  App,
  Button,
  DatePicker,
  Form,
  Input,
  Modal,
  Select,
  Space,
  Statistic,
  Typography
} from "antd";
import dayjs from "dayjs";
import { PlusOutlined, ReloadOutlined, SearchOutlined } from "@ant-design/icons";
import KnowledgeTable from "../components/KnowledgeTable";
import {
  createKnowledge,
  deleteKnowledge,
  getSubjects,
  getTags,
  listKnowledge,
  searchKnowledge,
  updateKnowledge
} from "../services/api";
import type { KnowledgeItem, KnowledgePreview, SubjectItem } from "../types/api";

const subjectColors: Record<string, string> = {
  政治: "#c1666b",
  英语: "#5b9aa0",
  数学: "#8a7290",
  计算机: "#5a8dee",
  其他: "#a08c6a"
};

const { RangePicker } = DatePicker;

interface KnowledgeFilters {
  query: string;
  subject?: string;
  tag?: string;
  date_from?: string;
  date_to?: string;
}

export default function KnowledgePage() {
  const { message } = App.useApp();
  const [items, setItems] = useState<KnowledgeItem[]>([]);
  const [subjects, setSubjects] = useState<SubjectItem[]>([]);
  const [tags, setTags] = useState<string[]>([]);
  const [subjectCounts, setSubjectCounts] = useState<Record<string, number>>({});
  const [loading, setLoading] = useState(false);
  const [query, setQuery] = useState("");
  const [subject, setSubject] = useState<string | undefined>();
  const [tag, setTag] = useState<string | undefined>();
  const [dateRange, setDateRange] = useState<[string, string] | undefined>();
  const [editing, setEditing] = useState<KnowledgeItem | null>(null);
  const [manualOpen, setManualOpen] = useState(false);
  const [creating, setCreating] = useState(false);
  const [editForm] = Form.useForm<KnowledgePreview>();
  const [manualForm] = Form.useForm<KnowledgePreview>();

  const subjectOptions = useMemo(
    () => subjects.map((item) => ({ label: item.name, value: item.name })),
    [subjects]
  );

  const totalCount = useMemo(
    () => Object.values(subjectCounts).reduce((sum, count) => sum + count, 0),
    [subjectCounts]
  );

  const currentFilters = (overrides: Partial<KnowledgeFilters> = {}): KnowledgeFilters => ({
    query,
    subject,
    tag,
    date_from: dateRange?.[0],
    date_to: dateRange?.[1],
    ...overrides
  });

  const matchesKeyword = (item: KnowledgeItem, keyword: string) => {
    const normalized = keyword.trim().toLowerCase();
    if (!normalized) return true;
    return [item.content, item.subject, ...item.tags].some((value) =>
      value.toLowerCase().includes(normalized)
    );
  };

  const matchesDateRange = (item: KnowledgeItem, filters: KnowledgeFilters) => {
    const day = item.created_at.slice(0, 10);
    if (filters.date_from && day < filters.date_from) return false;
    if (filters.date_to && day > filters.date_to) return false;
    return true;
  };

  const mergeKnowledge = (primary: KnowledgeItem[], fallback: KnowledgeItem[]) => {
    const seen = new Set<number>();
    return [...primary, ...fallback].filter((item) => {
      if (seen.has(item.id)) return false;
      seen.add(item.id);
      return true;
    });
  };

  const refreshCounts = async () => {
    const result = await listKnowledge({ limit: 1000 });
    const nextCounts = result.results.reduce<Record<string, number>>((acc, item) => {
      acc[item.subject] = (acc[item.subject] ?? 0) + 1;
      return acc;
    }, {});
    setSubjectCounts(nextCounts);
  };

  const refreshMeta = async () => {
    const [subjectResult, tagResult] = await Promise.all([getSubjects(), getTags()]);
    setSubjects(subjectResult.subjects);
    setTags(tagResult.tags);
  };

  const load = async (filters = currentFilters()) => {
    setLoading(true);
    try {
      if (filters.query.trim()) {
        const keyword = filters.query.trim();
        const [semanticResult, listResult] = await Promise.all([
          searchKnowledge({
            query: keyword,
            subject: filters.subject,
            top_k: 20
          }),
          listKnowledge({
            subject: filters.subject,
            tag: filters.tag,
            date_from: filters.date_from,
            date_to: filters.date_to,
            limit: 1000
          })
        ]);
        const semanticItems = semanticResult.results.filter(
          (item) =>
            (!filters.tag || item.tags.includes(filters.tag)) && matchesDateRange(item, filters)
        );
        const keywordItems = listResult.results.filter((item) => matchesKeyword(item, keyword));
        setItems(mergeKnowledge(semanticItems, keywordItems));
      } else {
        const result = await listKnowledge({
          subject: filters.subject,
          tag: filters.tag,
          date_from: filters.date_from,
          date_to: filters.date_to,
          limit: 100
        });
        setItems(result.results);
      }
    } catch (error) {
      message.error(error instanceof Error ? error.message : "加载失败");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void refreshMeta();
    void refreshCounts();
    void load({ query: "" });
  }, []);

  const selectSubject = (nextSubject?: string) => {
    setSubject(nextSubject);
    setQuery("");
    void load(currentFilters({ query: "", subject: nextSubject }));
  };

  const openEdit = (item: KnowledgeItem) => {
    setEditing(item);
    editForm.setFieldsValue({
      content: item.content,
      subject: item.subject,
      tags: item.tags
    });
  };

  const saveEdit = async () => {
    if (!editing) return;
    const values = await editForm.validateFields();
    try {
      await updateKnowledge(editing.id, values);
      message.success("已更新");
      setEditing(null);
      void refreshMeta();
      void refreshCounts();
      void load(currentFilters());
    } catch (error) {
      message.error(error instanceof Error ? error.message : "更新失败");
    }
  };

  const openManualCreate = () => {
    manualForm.setFieldsValue({
      content: "",
      subject: subject ?? subjects[0]?.name ?? "其他",
      tags: []
    });
    setManualOpen(true);
  };

  const saveManual = async () => {
    const values = await manualForm.validateFields();
    setCreating(true);
    try {
      const item = await createKnowledge({
        ...values,
        tags: values.tags ?? [],
        auto_categorize: false
      });
      message.success(`已保存 #${item.id}`);
      setManualOpen(false);
      manualForm.resetFields();
      void refreshMeta();
      void refreshCounts();
      void load(currentFilters());
    } catch (error) {
      message.error(error instanceof Error ? error.message : "保存失败");
    } finally {
      setCreating(false);
    }
  };

  const remove = async (item: KnowledgeItem) => {
    try {
      await deleteKnowledge(item.id);
      message.success("已删除");
      void refreshMeta();
      void refreshCounts();
      void load(currentFilters());
    } catch (error) {
      message.error(error instanceof Error ? error.message : "删除失败");
    }
  };

  const resetFilters = () => {
    setQuery("");
    setSubject(undefined);
    setTag(undefined);
    setDateRange(undefined);
    void load({ query: "", subject: undefined, tag: undefined, date_from: undefined, date_to: undefined });
  };

  return (
    <div className="page-stack">
      <div className="page-toolbar">
        <div>
          <Typography.Title level={3}>我的知识库</Typography.Title>
          <Typography.Text type="secondary">
            语义检索 + 关键词兜底，帮你从自己的笔记里找答案
          </Typography.Text>
        </div>
        <Space align="center">
          <Statistic title="已加载" value={items.length} />
          <Button
            type="primary"
            icon={<PlusOutlined />}
            aria-label="手动保存"
            onClick={openManualCreate}
          >
            手动保存
          </Button>
        </Space>
      </div>

      <div className="subject-chip-bar" aria-label="学科筛选">
        <button
          type="button"
          className={`subject-chip ${!subject ? "active" : ""}`}
          onClick={() => selectSubject(undefined)}
        >
          <span className="subject-dot all" />
          <span>全部</span>
          <strong>{totalCount}</strong>
        </button>

        {subjects.map((item) => (
          <button
            key={item.name}
            type="button"
            className={`subject-chip ${subject === item.name ? "active" : ""}`}
            onClick={() => selectSubject(item.name)}
          >
            <span
              className="subject-dot"
              style={{ backgroundColor: subjectColors[item.name] ?? "#64748b" }}
            />
            <span>{item.name}</span>
            <strong>{subjectCounts[item.name] ?? 0}</strong>
          </button>
        ))}
      </div>

      <section className="knowledge-main-panel">
        <div className="filter-bar knowledge-filter-bar">
          <Input
            allowClear
            prefix={<SearchOutlined />}
            value={query}
            placeholder={subject ? `在「${subject}」里搜索` : "语义/关键词搜索"}
            onChange={(event) => setQuery(event.target.value)}
            onPressEnter={() => load(currentFilters())}
          />
          <Select
            allowClear
            showSearch
            placeholder="标签"
            value={tag}
            options={tags.map((item) => ({ label: item, value: item }))}
            onChange={setTag}
          />
          <RangePicker
            value={dateRange ? [dayjs(dateRange[0]), dayjs(dateRange[1])] : null}
            placeholder={["开始日期", "结束日期"]}
            onChange={(_, value) => {
              setDateRange(value[0] && value[1] ? [value[0], value[1]] : undefined);
            }}
          />
          <Space>
            <Button
              type="primary"
              icon={<SearchOutlined />}
              loading={loading}
              onClick={() => load(currentFilters())}
            >
              查询
            </Button>
            <Button icon={<ReloadOutlined />} onClick={resetFilters}>
              重置
            </Button>
          </Space>
        </div>

        <KnowledgeTable data={items} loading={loading} onEdit={openEdit} onDelete={remove} />
      </section>

      <Modal
        title="编辑知识点"
        open={Boolean(editing)}
        okText="保存"
        cancelText="取消"
        onCancel={() => setEditing(null)}
        onOk={saveEdit}
      >
        <Form form={editForm} layout="vertical">
          <Form.Item name="content" label="内容" rules={[{ required: true, message: "请输入内容" }]}>
            <Input.TextArea autoSize={{ minRows: 4, maxRows: 8 }} />
          </Form.Item>
          <Form.Item name="subject" label="学科" rules={[{ required: true, message: "请选择学科" }]}>
            <Select options={subjectOptions} />
          </Form.Item>
          <Form.Item name="tags" label="标签">
            <Select mode="tags" options={tags.map((item) => ({ label: item, value: item }))} />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title="手动保存知识点"
        open={manualOpen}
        okText="保存"
        cancelText="取消"
        confirmLoading={creating}
        okButtonProps={{ "aria-label": "保存" }}
        onCancel={() => setManualOpen(false)}
        onOk={saveManual}
      >
        <Form form={manualForm} layout="vertical">
          <Form.Item name="content" label="内容" rules={[{ required: true, message: "请输入内容" }]}>
            <Input.TextArea autoSize={{ minRows: 4, maxRows: 8 }} />
          </Form.Item>
          <Form.Item name="subject" label="学科" rules={[{ required: true, message: "请选择学科" }]}>
            <Select options={subjectOptions} />
          </Form.Item>
          <Form.Item name="tags" label="标签">
            <Select mode="tags" options={tags.map((item) => ({ label: item, value: item }))} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
