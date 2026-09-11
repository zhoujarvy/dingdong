"""SQLite 访问层：线程局部连接 + WAL 模式，建表与查询/执行助手。"""
import sqlite3
import threading
import time

from . import config

_local = threading.local()
_init_lock = threading.Lock()
_initialized = False

SCHEMA = """
CREATE TABLE IF NOT EXISTS terminals (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    code          TEXT NOT NULL UNIQUE,
    name          TEXT NOT NULL,
    created_at    TEXT NOT NULL,
    last_seen_at  TEXT NOT NULL,
    status        TEXT NOT NULL DEFAULT 'active',   -- active / revoked
    revoked_at    TEXT,
    revoke_reason TEXT,
    inbox_token   TEXT NOT NULL DEFAULT ''          -- 网页消息中心访问令牌
);

CREATE TABLE IF NOT EXISTS messages (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    terminal_id  INTEGER NOT NULL REFERENCES terminals(id),
    title        TEXT NOT NULL,
    content      TEXT NOT NULL DEFAULT '',
    sender       TEXT NOT NULL DEFAULT '',
    access_token TEXT NOT NULL,
    created_at   TEXT NOT NULL,      -- 接口收到时间
    pushed_at    TEXT,               -- WebSocket 送达时间（NULL=尚未送达）
    read_at      TEXT,               -- 阅读时间（NULL=未读）
    deleted_at   TEXT                -- 客户端删除时间（NULL=未删，软删）
);
CREATE INDEX IF NOT EXISTS idx_messages_terminal ON messages(terminal_id, deleted_at, id);

CREATE TABLE IF NOT EXISTS api_keys (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT NOT NULL,
    key        TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL,
    revoked_at TEXT
);
"""


def _conn() -> sqlite3.Connection:
    conn = getattr(_local, "conn", None)
    if conn is None:
        conn = sqlite3.connect(config.db_path(), timeout=10)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        _local.conn = conn
    return conn


def init_db() -> None:
    global _initialized
    with _init_lock:
        if _initialized:
            return
        conn = _conn()
        conn.executescript(SCHEMA)
        # 旧库迁移：补充 inbox_token 列并为存量终端回填
        cols = [r["name"] for r in query("PRAGMA table_info(terminals)")]
        if "inbox_token" not in cols:
            conn.execute("ALTER TABLE terminals ADD COLUMN inbox_token TEXT NOT NULL DEFAULT ''")
            conn.commit()
        conn.execute(
            "UPDATE terminals SET inbox_token = lower(hex(randomblob(16))) WHERE inbox_token = ''"
        )
        conn.commit()
        _initialized = True


def query(sql: str, params=()) -> list:
    """返回 dict 列表。"""
    cur = _conn().execute(sql, params)
    return [dict(r) for r in cur.fetchall()]


def query_one(sql: str, params=()):
    rows = query(sql, params)
    return rows[0] if rows else None


def execute(sql: str, params=()) -> int:
    """执行写语句，返回 lastrowid。"""
    conn = _conn()
    cur = conn.execute(sql, params)
    conn.commit()
    return cur.lastrowid
