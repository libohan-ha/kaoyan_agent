import { afterEach, expect, test, vi } from "vitest";
import { createKnowledge } from "./api";

afterEach(() => {
  vi.unstubAllGlobals();
});

test("creates knowledge manually without AI categorization", async () => {
  const fetchMock = vi.fn().mockResolvedValue({
    ok: true,
    json: async () => ({
      id: 7,
      content: "手动保存测试",
      subject: "数学",
      tags: ["线代"],
      created_at: "2026-06-19 10:00:00"
    })
  });
  vi.stubGlobal("fetch", fetchMock);

  await createKnowledge({
    content: "手动保存测试",
    subject: "数学",
    tags: ["线代"],
    auto_categorize: false
  });

  expect(fetchMock).toHaveBeenCalledTimes(1);
  expect(fetchMock).toHaveBeenCalledWith(
    "/api/knowledge",
    expect.objectContaining({
      method: "POST",
      body: JSON.stringify({
        content: "手动保存测试",
        subject: "数学",
        tags: ["线代"],
        auto_categorize: false
      })
    })
  );
});
