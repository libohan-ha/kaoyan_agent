# 产品需求文档 (PRD) — 考研 Agent

> 版本：v1.0  
> 日期：2026-06-18  
> 技术栈：React + FastAPI (Python) + SQLite + sqlite-vec

---

## 1. 产品背景与痛点

### 1.1 痛点

考研备考过程中，每天都在学新东西（政治知识点、英语长难句、数学公式、计算机算法……），但这些知识存在两个问题：

- **遗忘**：学了就忘，过几天完全想不起来当时学的什么。艾宾浩斯遗忘曲线告诉我们，不复习等于没学
- **散落**：知识点记在书本上、笔记 app 里、草稿纸上，用的时候找不到，更别提和别的知识点串联
- **被动**：传统笔记只能"存"，不能在你需要的时候主动推送给你复习

### 1.2 核心洞察

> 考研最该复习的，不是教科书，而是**你自己记录和总结过的知识点**。自己写的理解、自己的错题归纳、自己的记忆口诀，这些才是对"你"最有价值的东西。

需要一个系统，能帮你：
1. **随手记**——学到一个知识点，10 秒内录入，AI 帮你分类打标签
2. **随时查**——遇到不会的，先搜自己记过的，RAG 匹配 + AI 回答
3. **每天推**——每天早上自动推送昨天学的东西，不学就不知道该复习什么

---

## 2. 产品定位

**一句话定义：**  
一个以"考研知识点"为核心知识库的 AI Agent，帮助考研党记录、检索、每日复习自己的学习内容，并通过 RAG + AI 实现智能问答。

**差异化：**
| 对比对象 | 区别 |
|---------|------|
| 印象笔记 / Notion | 本产品不是"写笔记"，而是"AI 自动分类 + 向量检索 + 每日推送复习" |
| ChatGPT / 通用 AI | 本产品不只靠通用知识回答，而是**优先检索你自己记录过的知识点**，用你自己的理解来答 |
| Anki 间隔重复 | 本产品不做卡片，做**原文清单推送**，每天推送昨天学的全部内容，简单直接 |
| 传统错题本 | 本产品有 AI 语义检索，输入一个问题就能匹配到相关知识点，不用手动分类找 |

---

## 3. 用户角色

| 角色 | 说明 |
|:---|:---|
| **用户（你自己）** | 唯一用户。考研备考者，录入知识点、浏览库、与 AI 对话、接收每日复盘 |

单人项目，暂不考虑多用户/登录体系（可后续扩展）。

---

## 4. 功能需求

### 4.1 核心功能一：录入知识点 📝

| 功能 | 描述 |
|:---|:---|
| **AI 录入** | 用户输入一句话或一段话（知识点/错题/总结），AI 自动判断学科并提取标签 |
| **预览确认** | AI 分析后生成预览卡片（学科 + 标签），用户确认后保存（同时生成向量 embedding） |
| **自动分类** | 五大学科：政治、英语、数学、计算机、其他（考研心态/时间管理等） |
| **自动标签** | AI 提取关键词作为标签（如"马原""洛必达""TCP 三次握手""红黑树"） |
| **去重** | 相同内容不会重复录入（基于内容 hash） |
| **极简输入** | 首页输入框，像聊天一样自然，降低记录门槛 |

**用户故事：**  
> 刚学完 Dijkstra 最短路径算法，打开网站输一句话"今天学了 Dijkstra，贪心+优先队列优化，时间复杂度 O((V+E)logV)"，AI 自动识别为计算机学科、打上"图论""最短路径""贪心"标签，我点确认就存好了。

### 4.2 核心功能二：智能提问 💬

| 功能 | 描述 |
|:---|:---|
| **RAG 检索** | 用户提问时，系统先将问题做 embedding，在知识库中做向量相似度匹配 |
| **AI 回答** | 将命中的知识点作为上下文喂给 DeepSeek，生成基于"你自己的笔记"的回答 |
| **来源标注** | 回复中标注引用了哪条知识点（含学科、标签），可点击查看详情 |
| **多轮对话** | 保持对话上下文，连续追问 |

**用户故事：**  
> 忘了洛必达法则的适用条件，问 agent "洛必达法则什么时候不能用"，agent 搜索知识库找到了我之前记的笔记，告诉我"0/0 或 ∞/∞ 型才可以用，注意不是所有未定式都能直接洛"——这是我自己总结的，比教科书更容易记住。

### 4.3 核心功能三：每日复盘 📋

| 功能 | 描述 |
|:---|:---|
| **定时推送** | 每天 07:30 自动推送昨日新增的所有知识点（原文清单） |
| **按学科分组** | 推送内容按学科分组展示（政治 3 条 / 计算机 5 条 / …） |
| **空日提醒** | 昨天没记录任何知识点时，推送一条鼓励消息 |
| **推送通道** | 微信（WeClaw，生产）/ Console 日志（开发期兜底） |
| **复盘页** | 前端提供"今日复盘"页面，随时查看昨天/今天学了什么 |

**用户故事：**  
> 早上 7:30 微信收到推送："📚 考研复盘 2026-06-18（8条）\n\n### 计算机（5）\n1. Dijkstra 算法...\n2. 红黑树插入...\n### 数学（3）\n1. 洛必达法则..."——一眼看完昨天学了什么，哪些该再看一遍一目了然。

### 4.4 辅助功能：知识库浏览 📖

| 功能 | 描述 |
|:---|:---|
| **列表浏览** | 按时间倒序展示所有知识点 |
| **学科筛选** | 按"政治/英语/数学/计算机/其他"过滤 |
| **标签筛选** | 按标签过滤 |
| **日期筛选** | 查看某天或某段时间的记录 |
| **搜索** | 语义搜索（向量检索）+ 关键词搜索 |

---

## 5. AI Agent 设计

这是本产品的核心——不是简单的 API 调用，而是具备**意图识别 + 工具调用能力**的 Agent。

### 5.1 Agent 能力矩阵

| 能力 | 类型 | 说明 |
|:---|:---|:---|
| 意图识别 | 推理 + 关键词 | 判断用户输入是"记录/提问/复盘/闲聊"（关键词优先，LLM 兜底） |
| 知识分类 | 推理 + 工具 | 分析内容 → 调用 preview_knowledge（学科 + 标签） |
| 向量检索 | 工具调用 | 问题 → embedding → sqlite-vec 相似度匹配 |
| 智能回答 | 生成 | 结合命中的知识点 + DeepSeek 推理 → 生成回答 |
| 多轮对话 | 记忆 | 保持会话上下文，连续追问 |

### 5.2 工具（Function Calling）定义

```
工具 1: preview_knowledge(content, subject, tags)
  - 功能：分析知识点内容，返回学科分类和标签预览（不保存）
  - 触发：用户陈述知识点、说"记一下/学到了"

工具 2: search_knowledge(query, top_k)
  - 功能：语义搜索知识库（bge-m3 embedding + sqlite-vec 向量检索）
  - 返回：匹配的知识点列表（含相似度分数）
  - 触发：用户提问、描述问题

工具 3: search_by_subject(subject, top_k)
  - 功能：按学科查看知识点
  - 触发：用户说"看看数学的笔记"

工具 4: search_by_date(date)
  - 功能：按日期查询知识点
  - 触发：用户说"昨天记了什么""6月15号的记录"

工具 5: search_by_date_range(date_from, date_to)
  - 功能：按日期范围查询
  - 触发：用户说"最近一周的记录"

工具 6: get_yesterday_review()
  - 功能：获取昨日所有知识点（复盘用）
  - 触发：用户说"今日复盘""该复习了"
```

### 5.3 Agent 对话流程（典型场景）

```
场景一：记录知识点
─────────────────
用户输入: "今天学了虚拟内存的页面置换算法，FIFO LRU Clock 三种"
  ↓
Agent 识别: 包含"学了" → 保存意图 → 强制 tool_choice=required
  ↓
Agent 调用: preview_knowledge(content="...", subject="计算机", tags=["操作系统","虚拟内存","页面置换"])
  ↓
前端渲染: 预览卡片 → 用户点"确认保存"
  ↓
后端执行: 写入 knowledge 表 + 生成 bge-m3 embedding + 写入 knowledge_vec

场景二：RAG 提问
─────────────────
用户输入: "页面置换算法有哪些？各有什么优缺点？"
  ↓
Agent 识别: 包含"？" → 提问意图 → 调用 search_knowledge
  ↓
向量检索: query embedding → sqlite-vec 检索 → 命中 3 条知识点
  ↓
Agent 回答: "根据你之前记录的笔记：① FIFO ... ② LRU ... ③ Clock ..."
          （引用来源：你 6.15 记的"虚拟内存笔记"）

场景三：闲聊兜底
─────────────────
用户输入: "考研好累啊"
  ↓
Agent 识别: 非保存/非提问 → normal_chat → 纯文本生成
  ↓
Agent 回答: "理解你，考研确实是一场持久战。你已经坚持到今天了，就是胜利💪"
          （不会幻觉说"已保存"——有守门机制拦截）
```

---

## 6. 技术架构

### 6.1 技术选型

| 层级 | 技术 | 选型理由 |
|:---|:---|:---|
| **前端** | React 18 + Vite | 生态成熟，开发快 |
| **UI 组件库** | Ant Design | 开箱即用，美观，跟 `自己skills` 项目一致 |
| **后端** | FastAPI (Python) | 异步、自动 API 文档、好做定时任务 |
| **数据库** | SQLite | 单人项目，零运维，单文件备份 |
| **向量存储** | sqlite-vec 扩展 | 纯 SQLite 生态，ANN 索引检索快，一个 .db 存所有 |
| **Embedding** | 硅基流动 BAAI/bge-m3 (1024维) | 中文效果好的开源模型，API 稳定 |
| **对话 / 意图** | DeepSeek API (deepseek-chat) | 支持 Function Calling，性价比高 |
| **定时调度** | APScheduler | 嵌入 FastAPI，轻量，支持 cron 表达式 |
| **推送** | WeClaw（微信，生产）/ Console（开发） | 官方协议不封号，HTTP API 简单 |

### 6.2 数据库设计

**表：subjects（学科分类）**
| 字段 | 类型 | 说明 |
|:---|:---|:---|
| id | INTEGER PK | 自增 |
| name | VARCHAR(50) UNIQUE | 政治/英语/数学/计算机/其他 |
| description | TEXT | 学科描述 |

**表：knowledge（知识点核心表）**
| 字段 | 类型 | 说明 |
|:---|:---|:---|
| id | INTEGER PK | 自增 |
| content | TEXT NOT NULL | 知识点内容 |
| subject | VARCHAR(50) NOT NULL | 学科（外键 subjects.name） |
| tags | TEXT(JSON) | 标签列表，如 `["高数","极限"]` |
| source | VARCHAR(50) | 来源 manual/weclaw/api |
| content_hash | TEXT UNIQUE | 内容 SHA1，去重 |
| created_at | DATETIME | 创建时间 |
| updated_at | DATETIME | 更新时间 |
| deleted_at | DATETIME | 软删除时间（NULL=未删除） |

**虚拟表：knowledge_vec（向量索引，sqlite-vec）**
| 字段 | 类型 | 说明 |
|:---|:---|:---|
| knowledge_id | INTEGER PK | 关联 knowledge.id |
| embedding | FLOAT[1024] | bge-m3 向量 |

**表：chat_sessions / chat_messages（对话持久化）**
| 字段 | 说明 |
|:---|:---|
| sessions: id, title, created_at, updated_at | 会话列表 |
| messages: id, session_id, role, content, matched_knowledge(JSON), preview(JSON), thoughts(JSON), created_at | 消息详情 |

**表：review_logs（复盘推送记录）**
| 字段 | 说明 |
|:---|:---|
| id, review_date, knowledge_ids(JSON), pushed_at, channel | 每次推送的日志 |

### 6.3 API 接口设计

```
# Agent 对话（SSE 流式）
POST /api/agent/chat
  Request:  { message: str, mode: "save"|"ask"|"auto", history: [...], session_id?: int }
  Response: SSE 流 (thought → reply/token → matched/preview → done)

# 知识点 CRUD
POST   /api/knowledge/preview     # AI 分析预览（不保存）
POST   /api/knowledge/confirm     # 确认保存
POST   /api/knowledge             # 外部 API 直接新建（WeClaw skill 用）
POST   /api/knowledge/search      # 语义检索 / 筛选
GET    /api/knowledge             # 列表（支持 subject/tag/date 过滤）
GET    /api/knowledge/{id}        # 详情
PUT    /api/knowledge/{id}        # 更新
DELETE /api/knowledge/{id}        # 软删除
POST   /api/knowledge/{id}/restore  # 恢复

# 复盘
GET    /api/review/yesterday       # 昨日复盘
GET    /api/review/today           # 今日记录
POST   /api/review/trigger         # 手动触发推送（测试）
GET    /api/review/logs            # 推送历史

# 会话
GET    /api/sessions               # 会话列表
GET    /api/sessions/{id}          # 会话详情 + 消息
DELETE /api/sessions/{id}          # 删除会话

# 健康
GET    /health
```

### 6.4 推送架构

```
APScheduler (每天 07:30, Asia/Shanghai)
    │
    ▼
review_service.run_daily_review()
    │
    ├─ 查 knowledge 表：WHERE date(created_at) = 昨天
    ├─ 有记录 → build_review_content() → 按学科分组 → Markdown 清单
    └─ notifier.send(title, content)
         ├── ConsoleNotifier: print 到日志（开发期默认）
         └── WeClawNotifier: HTTP POST → 微信（生产，URL 配置在 .env）
```

推送通道做成抽象基类 `BaseNotifier`，WeClaw 是一个实现。未来可扩展：
- 企业微信自建应用
- 邮件推送
- 钉钉机器人

### 6.5 页面结构

```
/                       ← 对话页（首页）：输入框 + SSE 流式对话 + 预览卡片
/knowledge              ← 知识库：按学科/标签/日期浏览 + 搜索
/review                 ← 复盘页：查看昨日/今日的复习清单
```

---

## 7. 体验设计要求

### 7.1 录入要轻
- 首页就是一个输入框，像聊天一样，说一句话就行
- AI 自动识别学科、提取标签，你只管点"确认"
- 从"想到"到"存好"不超过 10 秒

### 7.2 检索要准
- 用 bge-m3 做语义匹配，不是简单关键词
- "最短路径算法"能匹配到"Dijkstra"，"极限怎么求"能匹配到"洛必达"
- 命中结果按相关度排序，标注学科和标签

### 7.3 对话要自然
- Agent 能区分"我在记东西"和"我在问问题"，不用手动切模式
- 偶尔闲聊也能接住（"考研好累啊" → 鼓励回复，不会报错）
- 多轮追问能记住上下文
- **防幻觉守门**：模型在自由文本里宣称"已保存"时自动纠正

### 7.4 复盘要准时
- 每天 7:30 推送，雷打不动
- 只推昨天学的（没学的不推）
- 原文清单，不转提问式，一眼看完

---

## 8. WeClaw 对接（API Skill）

项目预留了 `skills/kaoyan-agent-api/SKILL.md`，供 WeClaw 的 AI 调用。

部署流程（后续实现）：
1. 将考研 Agent 部署到服务器（`python main.py`）
2. WeClaw 通过 SKILL.md 了解到可用的 API 接口
3. 用户在微信里说"记录一下 XXX"，WeClaw 的 AI 调用 `POST /api/knowledge` 保存
4. 每日复盘走后端定时任务 + WeClaw 推送 API

---

## 9. 迭代路线图

| 阶段 | 内容 | 目标 |
|:---|:---|:---|
| **V1.0 MVP** | 后端核心（保存/检索/对话）；每日复盘推送；简洁前端三页面 | 跑通完整闭环 ✅ 当前 |
| **V1.1** | 知识点编辑/删除；标签管理；UI 打磨；暗色模式 | 体验完善 |
| **V1.2** | WeClaw SKILL.md 完善；微信双向对话（通过 API）；推送渠道切换 | 微信集成 |
| **V2.0** | 多用户；移动端适配；知识图谱；历年真题关联 | 扩展能力 |

---

## 10. 成功标准

1. **你自己愿意天天用** —— 学完一个知识点，下意识打开网站记一句
2. **每天早上看复盘有收获** —— 看到昨天记的东西，"哦这个我还得再看一遍"
3. **提问能命中** —— 问一个之前记过的问题，agent 能找到你的笔记并基于它回答
4. **录入零负担** —— 从"想到"到"存好"不超过 10 秒

---

> 本 PRD 基于与用户的讨论整理而成，记录了产品的核心定位、功能需求与技术方案，作为后续开发和迭代的指导文档。
