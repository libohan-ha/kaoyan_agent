---
name: kaoyan-agent-api
description: Use the Kaoyan Agent HTTP API to record, preview, search, read, edit, soft-delete, restore, and review graduate-exam knowledge points. Use when an agent needs to save a 考研 knowledge point, search the user's notes, list notes by subject/tag/date, update or delete a note, fetch yesterday/today review content, or answer requests like "记录一下这个考点", "搜一下最短路径", "看看数学笔记", "今日复盘", or "昨天学了什么".
---

# Kaoyan Agent API

Use this skill to operate the Kaoyan Agent knowledge-base backend through HTTP APIs.

Default base URL: `http://localhost:8000`. Scripts also read `KAOYAN_AGENT_API_BASE_URL`.

## Workflow Rules

1. Record only content the user explicitly wants saved.
2. Prefer `preview` before `record` when the user expects confirmation.
3. Search before editing or deleting when the user gives a vague description instead of an ID.
4. Use soft delete by default. There is no hard-delete endpoint.
5. For dated requests, use exact `YYYY-MM-DD` dates. Convert relative dates only when the current date is known.
6. If the API is unavailable, tell the user to start the backend with `cd backend && python main.py`.
7. If embedding or AI keys are missing, report the exact backend error instead of inventing a fallback save.

## Script

Prefer `scripts/kaoyan.py` for all operations:

```bash
python scripts/kaoyan.py preview "Dijkstra 是单源最短路径算法"
python scripts/kaoyan.py record "Dijkstra 是单源最短路径算法" --subject 计算机 --tag 图论 --tag 最短路径
python scripts/kaoyan.py search "最短路径算法" --top-k 5
python scripts/kaoyan.py list --subject 数学
python scripts/kaoyan.py date 2026-06-18
python scripts/kaoyan.py range 2026-06-01 2026-06-18
python scripts/kaoyan.py get 123
python scripts/kaoyan.py update 123 --content "更新后的完整知识点" --subject 计算机 --tag 操作系统
python scripts/kaoyan.py delete 123
python scripts/kaoyan.py restore 123
python scripts/kaoyan.py review yesterday
python scripts/kaoyan.py review today
python scripts/kaoyan.py subjects
python scripts/kaoyan.py tags
```

`scripts/record_knowledge.py` remains available for record-only compatibility.

## API Reference

Create directly:

```http
POST /api/knowledge
```

```json
{
  "content": "用户明确要求保存的考研知识点",
  "subject": "计算机",
  "tags": ["图论", "最短路径"],
  "auto_categorize": true
}
```

Preview and confirm:

```http
POST /api/knowledge/preview
POST /api/knowledge/confirm
```

Search:

```http
POST /api/knowledge/search
```

```json
{
  "query": "最短路径算法",
  "top_k": 8,
  "subject": "计算机",
  "tag": "图论",
  "date": "2026-06-18",
  "date_from": "2026-06-01",
  "date_to": "2026-06-18"
}
```

Read, edit, delete, restore:

```http
GET    /api/knowledge/{id}
PUT    /api/knowledge/{id}
DELETE /api/knowledge/{id}
POST   /api/knowledge/{id}/restore
```

Review:

```http
GET  /api/review/yesterday
GET  /api/review/today
POST /api/review/trigger
GET  /api/review/logs
```

Valid subjects: `政治`, `英语`, `数学`, `计算机`, `其他`.
