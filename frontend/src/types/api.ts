export type SubjectName = "政治" | "英语" | "数学" | "计算机" | "其他";

export interface KnowledgeItem {
  id: number;
  content: string;
  subject: SubjectName | string;
  tags: string[];
  source?: string;
  score?: number;
  created_at: string;
  updated_at?: string;
}

export interface KnowledgePreview {
  content: string;
  subject: SubjectName | string;
  tags: string[];
}

export interface KnowledgeCreatePayload extends KnowledgePreview {
  auto_categorize?: boolean;
}

export interface SubjectItem {
  id: number;
  name: SubjectName | string;
  description: string;
}

export interface ReviewResponse {
  date: string;
  count: number;
  items: KnowledgeItem[];
  title?: string;
  content?: string;
}

export interface ReviewLog {
  id: number;
  review_date: string;
  knowledge_ids: number[];
  pushed_at: string;
  channel: string;
}

export interface ChatSession {
  id: number;
  title: string;
  created_at: string;
  updated_at?: string;
}

export interface StoredChatMessage {
  id: number;
  role: "user" | "assistant";
  content: string;
  matched_knowledge: KnowledgeItem[];
  preview?: KnowledgePreview | null;
  thoughts: string[];
  created_at: string;
}

export type ChatMode = "auto" | "save" | "ask";

export type SseEvent =
  | { type: "thought_start" | "thought_end" | "done"; session_id?: number }
  | { type: "thought" | "reply" | "token" | "error"; content: string }
  | { type: "preview"; data: KnowledgePreview }
  | { type: "matched"; data: KnowledgeItem[] };

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  thoughts?: string[];
  preview?: KnowledgePreview;
  matched?: KnowledgeItem[];
  error?: boolean;
}
