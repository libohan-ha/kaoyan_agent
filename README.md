# 考研 Agent

一个以"考研知识点"为核心知识库的 AI Agent 平台：录入知识点（AI 自动分学科/打标签）、浏览检索知识库、对话中 RAG 匹配、每日 7:30 推送昨日记录的复盘清单。

## 技术栈

- 后端：FastAPI + SQLite + sqlite-vec + DeepSeek + 硅基流动 bge-m3 + APScheduler
- 前端：React 18 + Vite + react-router-dom + Ant Design
- 推送：WeClaw（预留）/ Console 兜底

## 目录结构

```
考研agent/
├── backend/        FastAPI 后端
├── frontend/       React 前端
└── skills/         给 WeClaw 用的 API skill
```

## 快速开始

### 后端

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env   # 填入 API key
python main.py         # 启动在 http://localhost:8000
```

### 前端

```bash
cd frontend
npm install
npm run dev            # 启动在 http://localhost:5173
```

## 核心能力

1. **记录知识点**：输入一句话，AI 自动分学科（政治/英语/数学/计算机/其他）+ 提取标签 → 预览 → 确认保存（同时生成 embedding）
2. **RAG 提问**：问问题时向量检索知识库 → DeepSeek 结合命中知识点生成回答
3. **每日复盘**：每天 7:30 自动拉出昨天新增的知识点，整理成清单推送（WeClaw / Console）

## API 概览

- `POST /api/agent/chat` 对话（SSE 流式，含意图识别 + Function Calling）
- `POST /api/knowledge` 新建知识点
- `POST /api/knowledge/search` 语义检索
- `GET  /api/knowledge?subject=&date=` 列表/筛选
- `GET  /api/review/yesterday` 昨日复盘
- `GET  /api/sessions` 会话列表

外部工具（如 WeClaw）可参考 `skills/kaoyan-agent-api/SKILL.md` 调用。
