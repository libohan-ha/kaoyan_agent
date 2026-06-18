"""数据库连接与初始化（SQLite + sqlite-vec 扩展）。

sqlite-vec 通过 load_extension 加载，提供 knowledge_vec 虚拟表存储 bge-m3 的 1024 维向量，
避免全表扫描。元数据走原生 sqlite3 表，迁移风格沿用 自己skills 项目的自动加列。
"""
import sqlite3
import sqlite_vec
from config import DATABASE_PATH, EMBEDDING_DIM, DEFAULT_SUBJECTS


def get_connection() -> sqlite3.Connection:
    """获取一个已加载 sqlite-vec 扩展的连接。

    每次操作新建连接（FastAPI 下足够，单人项目零运维）。
    row_factory 设为 Row 以支持字典式访问。
    """
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    # sqlite-vec 需要启用扩展加载，然后加载
    conn.enable_load_extension(True)
    sqlite_vec.load(conn)
    conn.enable_load_extension(False)
    # 开启外键
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _add_column_if_missing(cursor, table: str, column: str, col_def: str):
    """幂等加列：若列不存在则 ALTER TABLE ADD COLUMN。"""
    cursor.execute(f"PRAGMA table_info({table})")
    columns = [row["name"] for row in cursor.fetchall()]
    if column not in columns:
        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_def}")


def init_db():
    """初始化所有表 + sqlite-vec 虚拟表 + 默认学科。幂等。"""
    conn = get_connection()
    cursor = conn.cursor()

    # ---- 学科分类 ----
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS subjects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name VARCHAR(50) UNIQUE NOT NULL,
            description TEXT
        )
    """)

    # ---- 知识点（核心表）----
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS knowledge (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT NOT NULL,
            subject VARCHAR(50) NOT NULL,
            tags TEXT DEFAULT '[]',
            source VARCHAR(50) DEFAULT 'manual',
            content_hash TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            deleted_at DATETIME
        )
    """)

    # ---- 对话会话 ----
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chat_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # ---- 对话消息 ----
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chat_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            matched_knowledge TEXT DEFAULT '[]',
            preview TEXT,
            thoughts TEXT DEFAULT '[]',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES chat_sessions(id) ON DELETE CASCADE
        )
    """)

    # ---- 复盘推送日志 ----
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS review_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            review_date DATE NOT NULL,
            knowledge_ids TEXT NOT NULL,
            pushed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            channel VARCHAR(50)
        )
    """)

    # ---- 自动加列（向前兼容）----
    _add_column_if_missing(cursor, "knowledge", "source", "VARCHAR(50) DEFAULT 'manual'")
    _add_column_if_missing(cursor, "knowledge", "content_hash", "TEXT")
    _add_column_if_missing(cursor, "knowledge", "deleted_at", "DATETIME")
    _add_column_if_missing(cursor, "chat_messages", "thoughts", "TEXT DEFAULT '[]'")

    # ---- 索引 ----
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_knowledge_subject
        ON knowledge(subject)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_knowledge_created_at
        ON knowledge(created_at)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_knowledge_deleted_at
        ON knowledge(deleted_at)
    """)

    # ---- sqlite-vec 虚拟表（存 1024 维向量）----
    # 用 IF NOT EXISTS 避免重复创建报错
    cursor.execute(f"""
        CREATE VIRTUAL TABLE IF NOT EXISTS knowledge_vec USING vec0(
            knowledge_id INTEGER PRIMARY KEY,
            embedding FLOAT[{EMBEDDING_DIM}]
        )
    """)

    # ---- 默认学科 ----
    for name, desc in DEFAULT_SUBJECTS:
        cursor.execute(
            "INSERT OR IGNORE INTO subjects (name, description) VALUES (?, ?)",
            (name, desc),
        )

    conn.commit()
    conn.close()


if __name__ == "__main__":
    init_db()
    print(f"Database initialized at {DATABASE_PATH}")
