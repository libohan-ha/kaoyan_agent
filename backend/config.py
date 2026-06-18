import os
from dotenv import load_dotenv
from pathlib import Path

# 加载 .env（支持 utf-8-sig BOM）
load_dotenv(Path(__file__).with_name(".env"), encoding="utf-8-sig")


# ===== DeepSeek（对话 / 意图识别 / 工具调用）=====
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

# ===== 硅基流动（Embedding）=====
SILICONFLOW_API_KEY = os.getenv("SILICONFLOW_API_KEY")
SILICONFLOW_EMBEDDING_MODEL = os.getenv("SILICONFLOW_EMBEDDING_MODEL", "BAAI/bge-m3")
SILICONFLOW_EMBEDDING_URL = os.getenv(
    "SILICONFLOW_EMBEDDING_URL", "https://api.siliconflow.cn/v1/embeddings"
)
SILICONFLOW_EMBEDDING_TIMEOUT = float(os.getenv("SILICONFLOW_EMBEDDING_TIMEOUT", "30"))

# ===== 检索参数 =====
SEARCH_DEFAULT_TOP_K = int(os.getenv("SEARCH_DEFAULT_TOP_K", "8"))
EMBEDDING_DIM = int(os.getenv("EMBEDDING_DIM", "1024"))

# ===== 服务 =====
HOST = os.getenv("HOST", "127.0.0.1")
PORT = int(os.getenv("PORT", "8000"))
DATABASE_PATH = os.path.join(os.path.dirname(__file__), "kaoyan.db")

# ===== 每日复盘推送 =====
def _parse_push_time(raw: str) -> tuple[int, int]:
    """解析 HH:MM → (hour, minute)，默认 07:30"""
    try:
        hh, mm = raw.strip().split(":")
        return int(hh), int(mm)
    except Exception:
        return 7, 30


REVIEW_PUSH_TIME = _parse_push_time(os.getenv("REVIEW_PUSH_TIME", "07:30"))
NOTIFIER_CHANNEL = os.getenv("NOTIFIER_CHANNEL", "console").strip().lower()

# ===== WeClaw 推送 =====
WECLAW_PUSH_URL = os.getenv("WECLAW_PUSH_URL", "").strip()
WECLAW_PUSH_TOKEN = os.getenv("WECLAW_PUSH_TOKEN", "").strip()

# ===== 默认学科（专业课 = 计算机）=====
DEFAULT_SUBJECTS = [
    ("政治", "马克思主义基本原理、毛中特、史纲、思修、时政"),
    ("英语", "英语一/二，单词、长难句、阅读、翻译、写作"),
    ("数学", "数学一/二/三，高数、线性代数、概率论"),
    ("计算机", "408 数据结构、计算机组成原理、操作系统、计算机网络"),
    ("其他", "未分类的知识点"),
]
