import { useCallback, useEffect, useMemo, useState } from "react";
import { NavLink, Navigate, Route, Routes, useLocation, useNavigate } from "react-router-dom";
import { BrowserRouter } from "react-router-dom";
import { Badge, Button, Drawer, Empty, Grid, Layout, Space, Spin, Typography } from "antd";
import { MenuOutlined, PlusOutlined, ReloadOutlined } from "@ant-design/icons";
import ChatPage from "./pages/ChatPage";
import KnowledgePage from "./pages/KnowledgePage";
import ReviewPage from "./pages/ReviewPage";
import { healthCheck, listSessions } from "./services/api";
import { CHAT_SESSIONS_UPDATED_EVENT, LAST_SESSION_KEY } from "./sessionState";
import type { ChatSession } from "./types/api";

const { Header, Content, Sider } = Layout;
const { useBreakpoint } = Grid;

function formatSessionTime(session: ChatSession) {
  const value = session.updated_at || session.created_at;
  return value ? value.slice(5, 16) : "最近";
}

function Shell() {
  const location = useLocation();
  const navigate = useNavigate();
  const screens = useBreakpoint();
  const [serviceOnline, setServiceOnline] = useState<boolean | null>(null);
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [sessionsLoading, setSessionsLoading] = useState(false);
  const isMobile = !screens.lg;

  const selectedSessionId = useMemo(() => {
    const value = new URLSearchParams(location.search).get("session");
    const parsed = Number(value);
    return Number.isInteger(parsed) && parsed > 0 ? parsed : undefined;
  }, [location.search]);

  const isChatRoute = location.pathname.startsWith("/chat");

  const checkService = async () => {
    try {
      const result = await healthCheck();
      setServiceOnline(result.status === "ok");
    } catch {
      setServiceOnline(false);
    }
  };

  const refreshSessions = useCallback(async () => {
    setSessionsLoading(true);
    try {
      const result = await listSessions();
      setSessions(result.sessions);
    } catch {
      setSessions([]);
    } finally {
      setSessionsLoading(false);
    }
  }, []);

  const startNewChat = () => {
    window.localStorage.removeItem(LAST_SESSION_KEY);
    navigate("/chat?new=1");
    setMobileNavOpen(false);
  };

  const openSession = (sessionId: number) => {
    navigate(`/chat?session=${sessionId}`);
    setMobileNavOpen(false);
  };

  useEffect(() => {
    void checkService();
  }, []);

  useEffect(() => {
    void refreshSessions();
    const onSessionsUpdated = () => {
      void refreshSessions();
    };
    window.addEventListener(CHAT_SESSIONS_UPDATED_EVENT, onSessionsUpdated);
    return () => {
      window.removeEventListener(CHAT_SESSIONS_UPDATED_EVENT, onSessionsUpdated);
    };
  }, [refreshSessions]);

  useEffect(() => {
    setMobileNavOpen(false);
  }, [location.pathname, location.search]);

  const sessionSidebarContent = (
    <>
      <div className="brand-block">
        <div className="brand-mark">研</div>
        <div>
          <Typography.Title level={4} className="brand-title">
            考研 Agent
          </Typography.Title>
          <Typography.Text type="secondary" className="brand-subtitle">
            历史对话
          </Typography.Text>
        </div>
      </div>
      <div className="session-sidebar-body">
        <div className="session-sidebar-header">
          <Typography.Text strong>对话列表</Typography.Text>
          <Button size="small" icon={<PlusOutlined />} onClick={startNewChat}>
            新对话
          </Button>
        </div>
        {sessionsLoading ? (
          <div className="session-sidebar-loading">
            <Spin size="small" />
          </div>
        ) : sessions.length === 0 ? (
          <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无历史对话" />
        ) : (
          <div className="session-list">
            {sessions.map((session) => (
              <button
                key={session.id}
                type="button"
                className={`session-nav-item ${
                  isChatRoute && selectedSessionId === session.id ? "active" : ""
                }`}
                onClick={() => openSession(session.id)}
              >
                <span className="session-nav-title">{session.title || `会话 #${session.id}`}</span>
                <span className="session-nav-meta">
                  #{session.id} · {formatSessionTime(session)}
                </span>
              </button>
            ))}
          </div>
        )}
      </div>
    </>
  );

  return (
    <Layout className="app-shell">
      {!isMobile && (
        <Sider width={240} className="app-sider" role="complementary" aria-label="对话列表">
          {sessionSidebarContent}
        </Sider>
      )}
      <Drawer
        className="mobile-nav-drawer"
        placement="left"
        width={260}
        open={mobileNavOpen}
        onClose={() => setMobileNavOpen(false)}
        closeIcon={null}
        styles={{ body: { padding: 0 } }}
      >
        <div role="complementary" aria-label="对话列表">
          {sessionSidebarContent}
        </div>
      </Drawer>

      <Layout>
        <Header className="app-header">
          <Space size={12}>
            {isMobile && (
              <Button
                className="mobile-nav-toggle"
                icon={<MenuOutlined />}
                aria-label={mobileNavOpen ? "关闭导航" : "打开导航"}
                onClick={() => setMobileNavOpen((open) => !open)}
              />
            )}
            <Space size={16} className="header-links">
              <NavLink to="/chat">对话</NavLink>
              <NavLink to="/knowledge">知识库</NavLink>
              <NavLink to="/review">复盘</NavLink>
            </Space>
          </Space>
          <Space>
            <Badge
              status={serviceOnline ? "success" : serviceOnline === false ? "error" : "default"}
              text={serviceOnline ? "后端在线" : serviceOnline === false ? "后端离线" : "检测中"}
            />
            <Button icon={<ReloadOutlined />} onClick={checkService}>
              刷新
            </Button>
          </Space>
        </Header>
        <Content className="app-content">
          <Routes>
            <Route path="/" element={<Navigate to="/chat" replace />} />
            <Route path="/chat" element={<ChatPage />} />
            <Route path="/knowledge" element={<KnowledgePage />} />
            <Route path="/review" element={<ReviewPage />} />
          </Routes>
        </Content>
      </Layout>
    </Layout>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <Shell />
    </BrowserRouter>
  );
}
