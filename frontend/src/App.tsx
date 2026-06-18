import { useEffect, useMemo, useState } from "react";
import { NavLink, Navigate, Route, Routes, useLocation, useNavigate } from "react-router-dom";
import { BrowserRouter } from "react-router-dom";
import { Badge, Button, Drawer, Grid, Layout, Menu, Space, Typography } from "antd";
import {
  BookOutlined,
  MenuOutlined,
  MessageOutlined,
  ReloadOutlined,
  ScheduleOutlined
} from "@ant-design/icons";
import ChatPage from "./pages/ChatPage";
import KnowledgePage from "./pages/KnowledgePage";
import ReviewPage from "./pages/ReviewPage";
import { healthCheck } from "./services/api";

const { Header, Content, Sider } = Layout;
const { useBreakpoint } = Grid;

function Shell() {
  const location = useLocation();
  const navigate = useNavigate();
  const screens = useBreakpoint();
  const [serviceOnline, setServiceOnline] = useState<boolean | null>(null);
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const isMobile = !screens.lg;

  const activeKey = useMemo(() => {
    if (location.pathname.startsWith("/knowledge")) return "/knowledge";
    if (location.pathname.startsWith("/review")) return "/review";
    return "/chat";
  }, [location.pathname]);

  const navItems = useMemo(
    () => [
      { key: "/chat", icon: <MessageOutlined />, label: "对话" },
      { key: "/knowledge", icon: <BookOutlined />, label: "知识库" },
      { key: "/review", icon: <ScheduleOutlined />, label: "复盘" }
    ],
    []
  );

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

  useEffect(() => {
    setMobileNavOpen(false);
  }, [location.pathname]);

  const navContent = (
    <>
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
        items={navItems}
        onClick={({ key }) => {
          navigate(key);
          setMobileNavOpen(false);
        }}
      />
    </>
  );

  return (
    <Layout className="app-shell">
      {!isMobile && (
        <Sider width={220} className="app-sider">
          {navContent}
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
        {navContent}
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
