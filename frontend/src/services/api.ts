import type {
  ChatMode,
  KnowledgeItem,
  KnowledgePreview,
  ReviewLog,
  ReviewResponse,
  SseEvent,
  SubjectItem
} from "../types/api";

const API_BASE = import.meta.env.VITE_API_BASE ?? "";

async function readJson<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `HTTP ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export async function healthCheck(): Promise<{ status: string; service: string }> {
  return readJson(await fetch(`${API_BASE}/health`));
}

export async function previewKnowledge(content: string): Promise<KnowledgePreview> {
  return readJson(
    await fetch(`${API_BASE}/api/knowledge/preview`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ content })
    })
  );
}

export async function confirmKnowledge(payload: KnowledgePreview): Promise<KnowledgeItem> {
  return readJson(
    await fetch(`${API_BASE}/api/knowledge/confirm`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    })
  );
}

export async function listKnowledge(params: {
  subject?: string;
  tag?: string;
  date?: string;
  date_from?: string;
  date_to?: string;
  limit?: number;
} = {}): Promise<{ results: KnowledgeItem[]; count: number }> {
  const query = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== "") query.set(key, String(value));
  });
  return readJson(await fetch(`${API_BASE}/api/knowledge?${query.toString()}`));
}

export async function searchKnowledge(payload: {
  query: string;
  top_k?: number;
  subject?: string;
}): Promise<{ results: KnowledgeItem[]; query: string; count: number }> {
  return readJson(
    await fetch(`${API_BASE}/api/knowledge/search`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    })
  );
}

export async function updateKnowledge(
  id: number,
  payload: KnowledgePreview
): Promise<KnowledgeItem> {
  return readJson(
    await fetch(`${API_BASE}/api/knowledge/${id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    })
  );
}

export async function deleteKnowledge(id: number): Promise<{ ok: boolean; id: number }> {
  return readJson(await fetch(`${API_BASE}/api/knowledge/${id}`, { method: "DELETE" }));
}

export async function getSubjects(): Promise<{ subjects: SubjectItem[] }> {
  return readJson(await fetch(`${API_BASE}/api/knowledge/subjects/list`));
}

export async function getTags(): Promise<{ tags: string[] }> {
  return readJson(await fetch(`${API_BASE}/api/knowledge/tags/list`));
}

export async function getYesterdayReview(): Promise<ReviewResponse> {
  return readJson(await fetch(`${API_BASE}/api/review/yesterday`));
}

export async function getTodayReview(): Promise<ReviewResponse> {
  return readJson(await fetch(`${API_BASE}/api/review/today`));
}

export async function triggerReview(): Promise<Record<string, unknown>> {
  return readJson(
    await fetch(`${API_BASE}/api/review/trigger`, {
      method: "POST"
    })
  );
}

export async function listReviewLogs(): Promise<{ logs: ReviewLog[] }> {
  return readJson(await fetch(`${API_BASE}/api/review/logs`));
}

export async function streamChat(
  payload: { message: string; mode: ChatMode; session_id?: number },
  onEvent: (event: SseEvent) => void
): Promise<number | undefined> {
  const response = await fetch(`${API_BASE}/api/agent/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });
  if (!response.ok || !response.body) {
    throw new Error(await response.text());
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let sessionId = payload.session_id;

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    const chunks = buffer.split("\n\n");
    buffer = chunks.pop() ?? "";

    for (const chunk of chunks) {
      const line = chunk
        .split("\n")
        .find((item) => item.startsWith("data:"));
      if (!line) continue;
      const event = JSON.parse(line.replace(/^data:\s*/, "")) as SseEvent;
      if (event.type === "done" && event.session_id) sessionId = event.session_id;
      onEvent(event);
    }
  }

  return sessionId;
}
