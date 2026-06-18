import { App as AntApp } from "antd";
import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import ChatPage from "./ChatPage";

const apiMocks = vi.hoisted(() => ({
  confirmKnowledge: vi.fn(),
  getSession: vi.fn(),
  listSessions: vi.fn(),
  streamChat: vi.fn()
}));

vi.mock("../services/api", () => apiMocks);

beforeEach(() => {
  vi.clearAllMocks();
  window.localStorage.setItem("kaoyan-agent:last-session-id", "12");
  apiMocks.getSession.mockResolvedValue({
    session: { id: 12, title: "树的高度", created_at: "2026-06-19 10:00:00" },
    messages: [
      {
        id: 101,
        role: "user",
        content: "树的高度怎么求",
        matched_knowledge: [],
        preview: null,
        thoughts: [],
        created_at: "2026-06-19 10:00:01"
      },
      {
        id: 102,
        role: "assistant",
        content: "树的高度 = max(左子树高度, 右子树高度) + 1",
        matched_knowledge: [],
        preview: null,
        thoughts: ["读取历史对话"],
        created_at: "2026-06-19 10:00:02"
      }
    ]
  });
  apiMocks.listSessions.mockResolvedValue({ sessions: [] });
});

afterEach(() => {
  window.localStorage.clear();
});

test("restores the last chat session after page refresh", async () => {
  render(
    <AntApp>
      <ChatPage />
    </AntApp>
  );

  await waitFor(() => expect(apiMocks.getSession).toHaveBeenCalledWith(12));
  expect(await screen.findByText("树的高度怎么求")).toBeInTheDocument();
  expect(screen.getByText("树的高度 = max(左子树高度, 右子树高度) + 1")).toBeInTheDocument();
});
