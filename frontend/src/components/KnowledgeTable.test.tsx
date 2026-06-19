import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, test, vi } from "vitest";
import KnowledgeTable from "./KnowledgeTable";
import type { KnowledgeItem } from "../types/api";

const item: KnowledgeItem = {
  id: 1,
  content: "求树的宽度：设置 width[level] 数组，递归传参并统计每一层节点数量。",
  subject: "计算机",
  tags: ["数据结构", "树"],
  created_at: "2026-06-19 10:00:00"
};

test("clicking content expands details and exposes edit action", async () => {
  const user = userEvent.setup();
  const onEdit = vi.fn();
  render(<KnowledgeTable data={[item]} onEdit={onEdit} />);

  await user.click(screen.getByRole("button", { name: "展开知识点详情" }));

  const detail = screen.getByLabelText("知识点详情");
  expect(detail).toHaveTextContent(item.content);

  await user.click(within(detail).getByRole("button", { name: "编辑" }));
  expect(onEdit).toHaveBeenCalledWith(item);
});
