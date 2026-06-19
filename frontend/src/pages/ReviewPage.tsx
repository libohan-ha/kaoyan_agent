import { useEffect, useState } from "react";
import { App, Button, Card, Empty, Segmented, Space, Statistic, Tag, Timeline, Typography } from "antd";
import { BellOutlined, CopyOutlined, ReloadOutlined } from "@ant-design/icons";
import {
  getTodayReview,
  getYesterdayReview,
  listReviewLogs,
  triggerReview
} from "../services/api";
import type { KnowledgeItem, ReviewLog, ReviewResponse } from "../types/api";
import MarkdownContent from "../components/MarkdownContent";

type ViewKey = "yesterday" | "today" | "logs";

export default function ReviewPage() {
  const { message } = App.useApp();
  const [view, setView] = useState<ViewKey>("yesterday");
  const [review, setReview] = useState<ReviewResponse | null>(null);
  const [logs, setLogs] = useState<ReviewLog[]>([]);
  const [loading, setLoading] = useState(false);
  const [triggering, setTriggering] = useState(false);

  const load = async (nextView = view) => {
    setLoading(true);
    try {
      if (nextView === "yesterday") {
        setReview(await getYesterdayReview());
      } else if (nextView === "today") {
        setReview(await getTodayReview());
      } else {
        const result = await listReviewLogs();
        setLogs(result.logs);
      }
    } catch (error) {
      message.error(error instanceof Error ? error.message : "加载失败");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load(view);
  }, [view]);

  const pushNow = async () => {
    setTriggering(true);
    try {
      const result = await triggerReview();
      message.success(result.success ? "已触发" : "触发完成但推送失败");
      void load(view);
    } catch (error) {
      message.error(error instanceof Error ? error.message : "触发失败");
    } finally {
      setTriggering(false);
    }
  };

  const groupedItems = (review?.items ?? []).reduce<Record<string, KnowledgeItem[]>>((acc, item) => {
    acc[item.subject] = [...(acc[item.subject] ?? []), item];
    return acc;
  }, {});

  const copyReview = async () => {
    if (!review?.content) return;
    try {
      await navigator.clipboard.writeText(review.content);
      message.success("已复制复盘内容");
    } catch {
      message.error("复制失败");
    }
  };

  return (
    <div className="page-stack">
      <div className="page-toolbar">
        <div>
          <Typography.Title level={3}>复盘</Typography.Title>
          <Typography.Text type="secondary">
            {review?.date ? `${review.date} · ${review.count} 条` : "推送记录"}
          </Typography.Text>
        </div>
        <Space>
          <Segmented
            value={view}
            options={[
              { label: "昨日", value: "yesterday" },
              { label: "今日", value: "today" },
              { label: "日志", value: "logs" }
            ]}
            onChange={(value) => setView(value as ViewKey)}
          />
          <Button icon={<ReloadOutlined />} loading={loading} onClick={() => load(view)}>
            刷新
          </Button>
          <Button type="primary" icon={<BellOutlined />} loading={triggering} onClick={pushNow}>
            触发推送
          </Button>
        </Space>
      </div>

      {view === "logs" ? (
        <Timeline
          className="logs-timeline"
          items={logs.map((log) => ({
            color: log.channel === "error" ? "red" : "blue",
            children: (
              <Space direction="vertical" size={2}>
                <Typography.Text strong>{log.review_date}</Typography.Text>
                <Typography.Text type="secondary">
                  {log.channel} · {log.pushed_at} · {log.knowledge_ids.length} 条
                </Typography.Text>
              </Space>
            )
          }))}
        />
      ) : (
        <div className="review-report">
          <div className="review-summary-grid">
            <Card className="review-summary-card" loading={loading}>
              <Statistic title={view === "today" ? "今日新增" : "昨日新增"} value={review?.count ?? 0} suffix="条" />
            </Card>
            <Card className="review-summary-card" loading={loading}>
              <Statistic title="覆盖学科" value={Object.keys(groupedItems).length} suffix="个" />
            </Card>
            <Card className="review-summary-card review-summary-copy" loading={loading}>
              <Typography.Text type="secondary">复盘日期</Typography.Text>
              <Typography.Title level={4}>{review?.date ?? "-"}</Typography.Title>
              <Button icon={<CopyOutlined />} disabled={!review?.content} onClick={copyReview}>
                复制复盘
              </Button>
            </Card>
          </div>

          {review?.content ? (
            <Card
              className="review-content-card"
              title={review.title ?? "复盘内容"}
              loading={loading}
            >
              <MarkdownContent content={review.content} className="review-markdown" />
            </Card>
          ) : null}

          {review?.items?.length ? (
            <div className="review-subject-sections">
              {Object.entries(groupedItems).map(([subject, items]) => (
                <Card
                  key={subject}
                  className="review-subject-card"
                  title={
                    <Space>
                      <Tag color="blue">{subject}</Tag>
                      <Typography.Text>{items.length} 条</Typography.Text>
                    </Space>
                  }
                >
                  <div className="review-knowledge-grid">
                    {items.map((item) => (
                      <article key={item.id} className="review-knowledge-card">
                        <Typography.Paragraph>{item.content}</Typography.Paragraph>
                        <Space size={[4, 4]} wrap>
                          {item.tags.map((tag) => (
                            <Tag key={tag}>{tag}</Tag>
                          ))}
                          <Tag>#{item.id}</Tag>
                        </Space>
                      </article>
                    ))}
                  </div>
                </Card>
              ))}
            </div>
          ) : (
            <Card className="review-empty-card" loading={loading}>
              <Empty description="暂无记录，今天先从记录一个知识点开始" />
            </Card>
          )}
        </div>
      )}
    </div>
  );
}
