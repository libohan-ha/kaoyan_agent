import argparse
import json
import os
import sys
import urllib.error
import urllib.request


def parse_args():
    parser = argparse.ArgumentParser(description="Record a knowledge point through the Kaoyan Agent API.")
    parser.add_argument("content", nargs="?", help="Knowledge content. Reads stdin when omitted.")
    parser.add_argument(
        "--base-url",
        default=os.getenv("KAOYAN_AGENT_API_BASE_URL", "http://localhost:8000"),
        help="Kaoyan Agent API base URL.",
    )
    parser.add_argument("--subject", choices=["政治", "英语", "数学", "计算机", "其他"], help="Optional subject.")
    parser.add_argument("--tag", action="append", default=[], help="Optional tag. Repeat for multiple tags.")
    parser.add_argument("--no-auto-categorize", action="store_true", help="Skip automatic subject/tag inference.")
    parser.add_argument("--timeout", type=float, default=45, help="Request timeout in seconds.")
    return parser.parse_args()


def read_content(value: str | None) -> str:
    content = value if value is not None else sys.stdin.read()
    content = content.strip()
    if not content:
        raise SystemExit("content is required")
    return content


def build_payload(args) -> dict:
    payload = {
        "content": read_content(args.content),
        "auto_categorize": not args.no_auto_categorize,
    }
    if args.subject:
        payload["subject"] = args.subject
    if args.tag:
        payload["tags"] = args.tag
    return payload


def post_json(url: str, payload: dict, timeout: float) -> dict:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code}: {body}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"request failed: {exc.reason}") from exc


def main() -> int:
    args = parse_args()
    try:
        result = post_json(f"{args.base_url.rstrip('/')}/api/knowledge", build_payload(args), args.timeout)
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
