import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import App from "./App";

let mockSessions: Array<{ id: number; title: string; updated_at: string }> = [];

function mockDesktopViewport() {
  vi.stubGlobal(
    "matchMedia",
    vi.fn().mockImplementation((query: string) => ({
      matches:
        query.includes("min-width: 992px") ||
        query.includes("min-width: 1200px") ||
        query.includes("min-width: 1600px"),
      media: query,
      onchange: null,
      addListener: vi.fn(),
      removeListener: vi.fn(),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      dispatchEvent: vi.fn()
    }))
  );
}

beforeEach(() => {
  window.localStorage.clear();
  mockSessions = [{ id: 12, title: "树的高度", updated_at: "2026-06-19 10:00:00" }];
  vi.stubGlobal(
    "fetch",
    vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      const method = init?.method ?? "GET";
      if (url.endsWith("/api/sessions/12") && method === "DELETE") {
        mockSessions = [];
        return Promise.resolve({
          ok: true,
          json: async () => ({ ok: true, id: 12 })
        });
      }
      if (url.endsWith("/api/sessions")) {
        return Promise.resolve({
          ok: true,
          json: async () => ({
            sessions: mockSessions
          })
        });
      }
      if (url.endsWith("/api/sessions/12")) {
        return Promise.resolve({
          ok: true,
          json: async () => ({
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
              }
            ]
          })
        });
      }
      return Promise.resolve({
        ok: true,
        json: async () => ({ status: "ok", service: "kaoyan-agent" })
      });
    })
  );
});

afterEach(() => {
  window.localStorage.clear();
  vi.unstubAllGlobals();
});

test("mobile navigation toggle opens and closes the drawer", async () => {
  const user = userEvent.setup();
  mockSessions = [];
  render(<App />);

  await user.click(screen.getByRole("button", { name: "打开导航" }));
  expect(await screen.findByRole("button", { name: "关闭导航" })).toBeInTheDocument();

  await user.click(screen.getByRole("button", { name: "关闭导航" }));
  expect(screen.getByRole("button", { name: "打开导航" })).toBeInTheDocument();
});

test("left sidebar shows chat sessions instead of page navigation", async () => {
  mockDesktopViewport();
  render(<App />);

  const sidebar = await screen.findByRole("complementary", { name: "对话列表" });
  expect(screen.getByRole("link", { name: "知识库" })).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "复盘" })).toBeInTheDocument();
  expect(sidebar).toHaveTextContent("树的高度");
  expect(sidebar).not.toHaveTextContent("知识库");
  expect(sidebar).not.toHaveTextContent("复盘");
});

test("header quick actions show knowledge and review instead of backend controls", () => {
  render(<App />);

  const quickActions = screen.getByRole("navigation", { name: "顶部快捷入口" });
  expect(within(quickActions).getByRole("link", { name: "知识库" })).toBeInTheDocument();
  expect(within(quickActions).getByRole("link", { name: "复盘" })).toBeInTheDocument();
  expect(screen.queryByText(/后端/)).not.toBeInTheDocument();
  expect(screen.queryByRole("button", { name: /刷新/ })).not.toBeInTheDocument();
});

test("desktop header keeps chat as the primary section link", () => {
  mockDesktopViewport();
  render(<App />);

  expect(screen.getByRole("link", { name: "对话" })).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "知识库" })).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "复盘" })).toBeInTheDocument();
});

test("left sidebar new chat clears the loaded conversation", async () => {
  const user = userEvent.setup();
  mockDesktopViewport();
  render(<App />);

  const sidebar = await screen.findByRole("complementary", { name: "对话列表" });
  expect(await screen.findByText("树的高度怎么求")).toBeInTheDocument();

  await user.click(within(sidebar).getByRole("button", { name: /新对话/ }));

  await waitFor(() => expect(screen.queryByText("树的高度怎么求")).not.toBeInTheDocument());
  expect(screen.getByText("暂无对话")).toBeInTheDocument();
});

test("left sidebar can delete a chat session", async () => {
  const user = userEvent.setup();
  mockDesktopViewport();
  render(<App />);

  const sidebar = await screen.findByRole("complementary", { name: "对话列表" });
  await user.click(within(sidebar).getByRole("button", { name: "删除会话 树的高度" }));

  await waitFor(() => expect(within(sidebar).queryByText("树的高度")).not.toBeInTheDocument());
  expect(globalThis.fetch).toHaveBeenCalledWith(
    "/api/sessions/12",
    expect.objectContaining({ method: "DELETE" })
  );
});
