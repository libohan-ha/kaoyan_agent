import { App as AntApp } from "antd";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, test, vi } from "vitest";
import KnowledgePage from "./KnowledgePage";

const apiMocks = vi.hoisted(() => ({
  createKnowledge: vi.fn(),
  deleteKnowledge: vi.fn(),
  getSubjects: vi.fn(),
  getTags: vi.fn(),
  listKnowledge: vi.fn(),
  searchKnowledge: vi.fn(),
  updateKnowledge: vi.fn()
}));

vi.mock("../services/api", () => apiMocks);

beforeEach(() => {
  vi.clearAllMocks();
  apiMocks.getSubjects.mockResolvedValue({
    subjects: [{ id: 1, name: "数学", description: "高数、线代、概率" }]
  });
  apiMocks.getTags.mockResolvedValue({ tags: ["线代"] });
  apiMocks.listKnowledge.mockResolvedValue({ results: [], count: 0 });
  apiMocks.createKnowledge.mockResolvedValue({
    id: 8,
    content: "手动保存知识",
    subject: "数学",
    tags: [],
    created_at: "2026-06-19 10:00:00"
  });
});

test("manual save submits knowledge without calling AI preview", async () => {
  const user = userEvent.setup();
  render(
    <AntApp>
      <KnowledgePage />
    </AntApp>
  );

  await user.click(await screen.findByRole("button", { name: "手动保存" }));
  const dialog = screen.getByRole("dialog", { name: "手动保存知识点" });

  await user.type(within(dialog).getByLabelText("内容"), "手动保存知识");
  await user.click(within(dialog).getByRole("button", { name: "保存" }));

  await waitFor(() => {
    expect(apiMocks.createKnowledge).toHaveBeenCalledWith({
      content: "手动保存知识",
      subject: "数学",
      tags: [],
      auto_categorize: false
    });
  });
}, 10000);
