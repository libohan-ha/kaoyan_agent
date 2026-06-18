"""快速验证 API 的临时脚本（测完即删）。

跑：python test_api.py
"""
import json
import urllib.parse
import urllib.request

BASE = "http://127.0.0.1:8000"


def post(path, payload):
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        f"{BASE}{path}",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))


def get(path):
    encoded_path = urllib.parse.quote(path, safe="/:?=&%")
    with urllib.request.urlopen(f"{BASE}{encoded_path}", timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def main():
    print("=" * 60)
    print("1. 测试 AI 预览（计算机知识点）")
    r = post("/api/knowledge/preview", {
        "content": "Dijkstra算法用于求解单源最短路径问题，基于贪心策略，使用优先队列优化后时间复杂度O((V+E)logV)"
    })
    print(json.dumps(r, ensure_ascii=False, indent=2))

    print("\n" + "=" * 60)
    print("2. 测试保存知识点（确认流程）")
    saved = post("/api/knowledge/confirm", {
        "content": r.get("content", "测试"),
        "subject": r.get("subject", "计算机"),
        "tags": r.get("tags", []),
    })
    print(json.dumps(saved, ensure_ascii=False, indent=2))

    print("\n" + "=" * 60)
    print("3. 再存一条数学知识点")
    math = post("/api/knowledge/confirm", {
        "content": "洛必达法则：求0/0或∞/∞型极限时，可以对分子分母分别求导后再求极限",
        "subject": "数学",
        "tags": ["高数", "极限", "洛必达"],
    })
    print(json.dumps(math, ensure_ascii=False, indent=2))

    print("\n" + "=" * 60)
    print("4. 测试语义检索（向量召回）")
    search = post("/api/knowledge/search", {
        "query": "最短路径算法",
        "top_k": 3,
    })
    print(json.dumps(search, ensure_ascii=False, indent=2))

    print("\n" + "=" * 60)
    print("5. 测试列表（按学科）")
    lst = get("/api/knowledge?subject=计算机")
    print(f"计算机学科共 {lst['count']} 条")

    print("\n" + "=" * 60)
    print("6. 测试昨日复盘")
    rev = get("/api/review/yesterday")
    print(f"昨日 {rev['count']} 条记录")
    print(rev["content"][:200])

    print("\n✅ 全部测试通过！")


if __name__ == "__main__":
    main()
