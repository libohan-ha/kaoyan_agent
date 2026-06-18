import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import App from "./App";

beforeEach(() => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ status: "ok", service: "kaoyan-agent" })
    })
  );
});

afterEach(() => {
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
