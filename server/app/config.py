"""配置加载：读取 server/config.json，缺省项使用默认值。"""
import json
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")

DEFAULTS = {
    "host": "0.0.0.0",
    "port": 8000,
    "admin_password": "admin123",
    "database": "dingdong.db",
    "terminal_offline_days": 30,   # 终端超过该天数未连接则自动注销
}

_cache = None


def _load() -> dict:
    global _cache
    if _cache is None:
        cfg = dict(DEFAULTS)
        if os.path.exists(CONFIG_PATH):
            try:
                with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                    cfg.update(json.load(f))
            except (json.JSONDecodeError, OSError):
                pass
        _cache = cfg
    return _cache


def get(key: str):
    return _load().get(key, DEFAULTS.get(key))


def db_path() -> str:
    db = get("database")
    return db if os.path.isabs(db) else os.path.join(BASE_DIR, db)
