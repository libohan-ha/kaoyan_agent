import { useEffect, useMemo, useState } from "react";
import { NavLink, Navigate, Route, Routes, useLocation, useNavigate } from "react-router-dom";
import { BrowserRouter } from "react-router-dom";
import { Badge, Button, Layout, Menu, Space, Typography } from "antd";
import {
  BookOutlined,
  MessageOutlined,
  ReloadOutlined,
  ScheduleOutlined
} from "@ant-design/icons";
import ChatPage from "./pages/ChatPage";
import KnowledgePage from "./pages/KnowledgePage";
import ReviewPage from "./pages/ReviewPage";
import { healthCheck } from "./services/api";

const { Header, Content, Sider } = Layout;

function Shell() {
  const location = useLocation();
  const navigate = useNavigate();
  const [serviceOnline, setServiceOnline] = useState<boolean | null>(null);

  const activeKey = useMemo(() => {
    if (location.pathname.startsWith("/knowledge")) return "/knowledge";
    if (location.pathname.startsWith("/review")) return "/review";
    return "/chat";
  }, [location.pathname]);

  const checkService = async () => {
    try {
      const result = await healthCheck();
      setServiceOnline(result.status === "ok");
    } catch {
      setServiceOnline(false);
    }
  };

  useEffect(() => {
    void checkService();
  }, []);

  return (
    <Layout className="app-shell">
      <Sider breakpoint="lg" collapsedWidth={0} width={220} className="app-sider">
        <div className="brand-block">
          <div className="brand-mark">研</div>
          <div>
            <Typography.Title level={4} className="brand-title">
              考研 Agent
            </Typography.Title>
            <Typography.Text type="secondary" className="brand-subtitle">
              个人知识库
            </Typography.Text>
          </div>
        </div>
        <Menu
          mode="inline"
          selectedKeys={[activeKey]}
          className="nav-menu"
          items={[
            { key: "/chat", icon: <MessageOutlined />, label: "对话" },
            { key: "/knowledge", icon: <BookOutlined />, label: "知识库" },
            { key: "/review", icon: <ScheduleOutlined />, label: "复盘" }
          ]}
          onClick={({ key }) => navigate(key)}
        />
      </Sider>

      <Layout>
        <Header className="app-header">
          <Space size={16}>
            <NavLink to="/chat">对话</NavLink>
            <NavLink to="/knowledge">知识库</NavLink>
            <NavLink to="/review">复盘</NavLink>
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
