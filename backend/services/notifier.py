"""推送通道抽象层。

当前实现：
- ConsoleNotifier: 打印到日志（开发期默认兜底）
- WeClawNotifier: HTTP POST 到 WeClaw 推送 API（生产用，URL/Token 后配）

扩展新通道只需继承 BaseNotifier 并在 get_notifier 里注册。
"""
import json
import urllib.error
import urllib.request
from abc import ABC, abstractmethod

from config import NOTIFIER_CHANNEL, WECLAW_PUSH_URL, WECLAW_PUSH_TOKEN


class BaseNotifier(ABC):
    """推送通道抽象基类。"""

    name: str = "base"

    @abstractmethod
    def send(self, title: str, content: str) -> dict:
        """推送一条消息。返回 {ok, detail}。"""
        ...


class ConsoleNotifier(BaseNotifier):
    """打印到标准输出/日志。开发期默认。"""

    name = "console"

    def send(self, title: str, content: str) -> dict:
        # 直接 print，部署时 uvicorn 会写到日志
        print(f"\n{'=' * 50}")
        print(f"[推送通知] {title}")
        print("-" * 50)
        print(content)
        print(f"{'=' * 50}\n")
        return {"ok": True, "detail": "printed to console"}


class WeClawNotifier(BaseNotifier):
    """通过 WeClaw 的主动推送 API 推送到微信。

    WeClaw 部署后会暴露一个 HTTP 接口用于主动推送（命令行或 HTTP）。
    配置项：WECLAW_PUSH_URL（接口地址）、WECLAW_PUSH_TOKEN（鉴权 token）。

    若 URL 未配置，send 会优雅降级为只打印（不报错，保证定时任务不崩）。
    """

    name = "weclaw"

    def __init__(self, url: str = "", token: str = ""):
        self.url = url or WECLAW_PUSH_URL
        self.token = token or WECLAW_PUSH_TOKEN

    def send(self, title: str, content: str) -> dict:
        if not self.url:
            print(
                f"\n[WeClaw 未配置] 跳过推送，标题: {title}\n（请在 .env 设置 WECLAW_PUSH_URL）\n"
            )
            return {"ok": False, "detail": "WECLAW_PUSH_URL not configured"}

        payload = {"title": title, "content": content}
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(
            self.url, data=data, headers=headers, method="POST"
        )
        try:
            with urllib.request.urlopen(request, timeout=15) as resp:
                body = resp.read().decode("utf-8", errors="replace")
            return {"ok": True, "detail": body}
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"WeClaw 推送失败 HTTP {exc.code}: {body}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"WeClaw 推送请求失败: {exc.reason}") from exc


def get_notifier() -> BaseNotifier:
    """根据 NOTIFIER_CHANNEL 配置返回对应通道。"""
    channel = (NOTIFIER_CHANNEL or "console").strip().lower()
    if channel == "weclaw":
        return WeClawNotifier()
    return ConsoleNotifier()
