import { useEffect, useState } from "react";
import { App, Button, Card, Empty, List, Segmented, Space, Tag, Timeline, Typography } from "antd";
import { BellOutlined, ReloadOutlined } from "@ant-design/icons";
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
        <Space direction="vertical" size={16} className="full-width">
          {review?.content && (
            <Card title={review.title ?? "复盘内容"} loading={loading}>
              <MarkdownContent content={review.content} className="review-markdown" />
            </Card>
          )}
          {review?.items?.length ? (
            <List
              dataSource={review.items}
              renderItem={(item: KnowledgeItem) => (
                <List.Item className="review-item">
                  <List.Item.Meta
                    title={
                      <Space wrap>
                        <Tag color="blue">{item.subject}</Tag>
                        {item.tags.map((tag) => (
                          <Tag key={tag}>{tag}</Tag>
                        ))}
                      </Space>
                    }
                    description={item.content}
                  />
                </List.Item>
              )}
            />
          ) : (
            <Empty description="暂无记录" />
          )}
        </Space>
      )}
    </div>
  );
}
