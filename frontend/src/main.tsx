import React from "react";
import ReactDOM from "react-dom/client";
import { ConfigProvider, App as AntApp } from "antd";
import zhCN from "antd/locale/zh_CN";
import "antd/dist/reset.css";
import "./styles.css";
import App from "./App";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <ConfigProvider
      locale={zhCN}
      theme={{
        token: {
          colorPrimary: "#2d6a4f",
          colorInfo: "#2d6a4f",
          colorLink: "#1b4332",
          borderRadius: 10,
          fontFamily:
            '-apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Microsoft YaHei", "Source Han Sans SC", sans-serif'
        },
        components: {
          Card: { borderRadiusLG: 14, colorBorderSecondary: "#e7e2d6" },
          Button: { borderRadius: 8 },
          Input: { borderRadius: 8, colorBorder: "#d8d2c2" },
          Select: { borderRadius: 8 },
          Modal: { borderRadiusLG: 14 },
          Tag: { borderRadiusSM: 6 },
          Segmented: { borderRadius: 8 },
          Drawer: { colorBgElevated: "#faf8f3" }
        }
      }}
    >
      <AntApp>
        <App />
      </AntApp>
    </ConfigProvider>
  </React.StrictMode>
);
