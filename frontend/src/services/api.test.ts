import { afterEach, expect, test, vi } from "vitest";
import { createKnowledge, deleteSession, getSession } from "./api";

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

test("loads a persisted chat session by id", async () => {
  const fetchMock = vi.fn().mockResolvedValue({
    ok: true,
    json: async () => ({
      session: { id: 12, title: "树的高度", created_at: "2026-06-19 10:00:00" },
      messages: [
        {
          id: 1,
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
  vi.stubGlobal("fetch", fetchMock);

  await getSession(12);

  expect(fetchMock).toHaveBeenCalledWith("/api/sessions/12");
});

test("deletes a persisted chat session by id", async () => {
  const fetchMock = vi.fn().mockResolvedValue({
    ok: true,
    json: async () => ({ ok: true, id: 12 })
  });
  vi.stubGlobal("fetch", fetchMock);

  await deleteSession(12);

  expect(fetchMock).toHaveBeenCalledWith(
    "/api/sessions/12",
    expect.objectContaining({ method: "DELETE" })
  );
});
