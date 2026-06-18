import { render, screen } from "@testing-library/react";
import { expect, test } from "vitest";
import MarkdownContent from "./MarkdownContent";

test("renders review markdown as structured content", () => {
  render(
    <MarkdownContent
      content={"**📚 2026-06-18 考研复盘**\n\n### 数学（2）\n\n1. 矩阵满秩 `线性代数`"}
      className="review-markdown"
    />
  );

  expect(screen.getByText("📚 2026-06-18 考研复盘")).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: "数学（2）" })).toBeInTheDocument();
  expect(screen.getByRole("listitem")).toHaveTextContent("矩阵满秩");
  expect(screen.getByText("线性代数").tagName).toBe("CODE");
});
