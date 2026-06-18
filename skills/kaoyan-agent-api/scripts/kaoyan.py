import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request


DEFAULT_BASE_URL = "http://localhost:8000"
SUBJECTS = ["政治", "英语", "数学", "计算机", "其他"]


def api_request(
    base_url: str,
    method: str,
    path: str,
    payload: dict | None = None,
    params: dict | None = None,
    timeout: float = 45,
) -> dict:
    url = f"{base_url.rstrip('/')}{path}"
    clean_params = {k: v for k, v in (params or {}).items() if v is not None and v != ""}
    if clean_params:
        url = f"{url}?{urllib.parse.urlencode(clean_params)}"

    data = None
    headers = {}
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8")
            return json.loads(body) if body else {"ok": True}
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code}: {body}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"request failed: {exc.reason}") from exc


def read_content(value: str | None) -> str:
    content = value if value is not None else sys.stdin.read()
    content = content.strip()
    if not content:
        raise SystemExit("content is required")
    return content


def add_common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--base-url",
        default=os.getenv("KAOYAN_AGENT_API_BASE_URL", DEFAULT_BASE_URL),
        help="Kaoyan Agent API base URL.",
    )
    parser.add_argument("--timeout", type=float, default=45, help="Request timeout in seconds.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Kaoyan Agent API client.")
    add_common(parser)
    subparsers = parser.add_subparsers(dest="command", required=True)

    preview = subparsers.add_parser("preview", help="Preview subject/tags without saving.")
    preview.add_argument("content", nargs="?", help="Knowledge content. Reads stdin when omitted.")

    record = subparsers.add_parser("record", help="Create a new knowledge point.")
    record.add_argument("content", nargs="?", help="Knowledge content. Reads stdin when omitted.")
    record.add_argument("--subject", choices=SUBJECTS, help="Optional subject.")
    record.add_argument("--tag", action="append", default=[], help="Optional tag. Repeat for multiple tags.")
    record.add_argument("--no-auto-categorize", action="store_true", help="Skip automatic subject/tag inference.")

    confirm = subparsers.add_parser("confirm", help="Save a previously reviewed preview.")
    confirm.add_argument("content", nargs="?", help="Knowledge content. Reads stdin when omitted.")
    confirm.add_argument("--subject", required=True, choices=SUBJECTS)
    confirm.add_argument("--tag", action="append", default=[], help="Tag. Repeat for multiple tags.")

    search = subparsers.add_parser("search", help="Semantic search or filtered list.")
    search.add_argument("query", nargs="?", help="Semantic query. Omit when filtering only.")
    search.add_argument("--top-k", type=int, default=8)
    search.add_argument("--subject", choices=SUBJECTS)
    search.add_argument("--tag")
    search.add_argument("--date", help="Single date in YYYY-MM-DD.")
    search.add_argument("--from", dest="date_from", help="Start date in YYYY-MM-DD.")
    search.add_argument("--to", dest="date_to", help="End date in YYYY-MM-DD.")
    search.add_argument("--deleted", action="store_true", help="List soft-deleted records when not using semantic query.")

    list_cmd = subparsers.add_parser("list", help="List knowledge points.")
    list_cmd.add_argument("--subject", choices=SUBJECTS)
    list_cmd.add_argument("--tag")
    list_cmd.add_argument("--date")
    list_cmd.add_argument("--from", dest="date_from")
    list_cmd.add_argument("--to", dest="date_to")
    list_cmd.add_argument("--deleted", action="store_true")
    list_cmd.add_argument("--limit", type=int, default=100)

    date = subparsers.add_parser("date", help="List knowledge from one date.")
    date.add_argument("date")
    date.add_argument("--subject", choices=SUBJECTS)
    date.add_argument("--tag")

    date_range = subparsers.add_parser("range", help="List knowledge from a date range.")
    date_range.add_argument("date_from")
    date_range.add_argument("date_to")
    date_range.add_argument("--subject", choices=SUBJECTS)
    date_range.add_argument("--tag")

    get = subparsers.add_parser("get", help="Get one knowledge point by ID.")
    get.add_argument("id", type=int)

    update = subparsers.add_parser("update", help="Update one knowledge point by ID, preserving omitted fields.")
    update.add_argument("id", type=int)
    update.add_argument("--content")
    update.add_argument("--subject", choices=SUBJECTS)
    update.add_argument("--tag", action="append", default=[], help="Replace tags. Repeat for multiple tags.")
    update.add_argument("--clear-tags", action="store_true")

    delete = subparsers.add_parser("delete", help="Soft-delete one knowledge point by ID.")
    delete.add_argument("id", type=int)

    restore = subparsers.add_parser("restore", help="Restore one soft-deleted knowledge point by ID.")
    restore.add_argument("id", type=int)

    review = subparsers.add_parser("review", help="Get review content or trigger push.")
    review.add_argument("kind", choices=["yesterday", "today", "logs", "trigger"])

    subparsers.add_parser("subjects", help="List subjects.")
    subparsers.add_parser("tags", help="List tags.")

    chat = subparsers.add_parser("chat", help="Send one chat message and print SSE events.")
    chat.add_argument("message", nargs="?", help="Message. Reads stdin when omitted.")
    chat.add_argument("--mode", choices=["auto", "save", "ask"], default="auto")
    chat.add_argument("--session-id", type=int)

    return parser


def command_preview(args) -> dict:
    return api_request(
        args.base_url,
        "POST",
        "/api/knowledge/preview",
        {"content": read_content(args.content)},
        timeout=args.timeout,
    )


def command_record(args) -> dict:
    payload = {
        "content": read_content(args.content),
        "auto_categorize": not args.no_auto_categorize,
    }
    if args.subject:
        payload["subject"] = args.subject
    if args.tag:
        payload["tags"] = args.tag
    return api_request(args.base_url, "POST", "/api/knowledge", payload, timeout=args.timeout)


def command_confirm(args) -> dict:
    payload = {"content": read_content(args.content), "subject": args.subject, "tags": args.tag}
    return api_request(args.base_url, "POST", "/api/knowledge/confirm", payload, timeout=args.timeout)


def command_search(args) -> dict:
    payload = {
        "query": args.query,
        "top_k": args.top_k,
        "subject": args.subject,
        "tag": args.tag,
        "date": args.date,
        "date_from": args.date_from,
        "date_to": args.date_to,
        "deleted": args.deleted,
    }
    return api_request(args.base_url, "POST", "/api/knowledge/search", payload, timeout=args.timeout)


def command_list(args) -> dict:
    params = {
        "subject": args.subject,
        "tag": args.tag,
        "date": args.date,
        "date_from": args.date_from,
        "date_to": args.date_to,
        "deleted": args.deleted,
        "limit": args.limit,
    }
    return api_request(args.base_url, "GET", "/api/knowledge", params=params, timeout=args.timeout)


def command_date(args) -> dict:
    params = {"date": args.date, "subject": args.subject, "tag": args.tag}
    return api_request(args.base_url, "GET", "/api/knowledge", params=params, timeout=args.timeout)


def command_range(args) -> dict:
    params = {
        "date_from": args.date_from,
        "date_to": args.date_to,
        "subject": args.subject,
        "tag": args.tag,
    }
    return api_request(args.base_url, "GET", "/api/knowledge", params=params, timeout=args.timeout)


def command_get(args) -> dict:
    return api_request(args.base_url, "GET", f"/api/knowledge/{args.id}", timeout=args.timeout)


def command_update(args) -> dict:
    current = command_get(args)
    tags = [] if args.clear_tags else (args.tag if args.tag else current.get("tags", []))
    payload = {
        "content": args.content if args.content is not None else current["content"],
        "subject": args.subject if args.subject is not None else current["subject"],
        "tags": tags,
    }
    return api_request(args.base_url, "PUT", f"/api/knowledge/{args.id}", payload, timeout=args.timeout)


def command_delete(args) -> dict:
    return api_request(args.base_url, "DELETE", f"/api/knowledge/{args.id}", timeout=args.timeout)


def command_restore(args) -> dict:
    return api_request(args.base_url, "POST", f"/api/knowledge/{args.id}/restore", timeout=args.timeout)


def command_review(args) -> dict:
    if args.kind == "trigger":
        return api_request(args.base_url, "POST", "/api/review/trigger", timeout=args.timeout)
    return api_request(args.base_url, "GET", f"/api/review/{args.kind}", timeout=args.timeout)


def command_subjects(args) -> dict:
    return api_request(args.base_url, "GET", "/api/knowledge/subjects/list", timeout=args.timeout)


def command_tags(args) -> dict:
    return api_request(args.base_url, "GET", "/api/knowledge/tags/list", timeout=args.timeout)


def command_chat(args) -> dict:
    payload = {
        "message": read_content(args.message),
        "mode": args.mode,
        "session_id": args.session_id,
    }
    response = urllib.request.urlopen(
        urllib.request.Request(
            f"{args.base_url.rstrip('/')}/api/agent/chat",
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        ),
        timeout=args.timeout,
    )
    events = []
    for raw_line in response:
        line = raw_line.decode("utf-8", errors="replace").strip()
        if not line.startswith("data:"):
            continue
        events.append(json.loads(line.replace("data:", "", 1).strip()))
    return {"events": events}


COMMANDS = {
    "preview": command_preview,
    "record": command_record,
    "confirm": command_confirm,
    "search": command_search,
    "list": command_list,
    "date": command_date,
    "range": command_range,
    "get": command_get,
    "update": command_update,
    "delete": command_delete,
    "restore": command_restore,
    "review": command_review,
    "subjects": command_subjects,
    "tags": command_tags,
    "chat": command_chat,
}


def main() -> int:
    args = build_parser().parse_args()
    try:
        result = COMMANDS[args.command](args)
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
