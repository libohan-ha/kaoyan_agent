import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import App from "./App";

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
  vi.stubGlobal(
    "fetch",
    vi.fn((input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/api/sessions")) {
        return Promise.resolve({
          ok: true,
          json: async () => ({
            sessions: [{ id: 12, title: "树的高度", updated_at: "2026-06-19 10:00:00" }]
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
  render(<App />);

  await user.click(screen.getByRole("button", { name: "打开导航" }));
  expect(screen.getByRole("button", { name: "关闭导航" })).toBeInTheDocument();

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
