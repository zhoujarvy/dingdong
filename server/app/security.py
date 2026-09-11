"""鉴权：管理后台会话 token 与第三方推送 API Key。"""
import time
from typing import Optional

from fastapi import Header, HTTPException

from . import config, db
from .utils import gen_admin_token

# 内存会话：token -> 过期时间戳（服务重启后需重新登录）
ADMIN_SESSIONS: dict = {}
SESSION_TTL = 12 * 3600


def create_session() -> str:
    token = gen_admin_token()
    ADMIN_SESSIONS[token] = time.time() + SESSION_TTL
    return token


def verify_password(password: str) -> bool:
    return password == config.get("admin_password")


def require_admin(authorization: str = Header(None)) -> str:
    """FastAPI 依赖：校验 Bearer token，返回 token。"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="未登录")
    token = authorization[7:].strip()
    expire = ADMIN_SESSIONS.get(token)
    if expire is None:
        raise HTTPException(status_code=401, detail="登录已失效")
    if time.time() > expire:
        ADMIN_SESSIONS.pop(token, None)
        raise HTTPException(status_code=401, detail="登录已过期")
    return token


def require_api_key(x_api_key: Optional[str] = Header(None)) -> str:
    """FastAPI 依赖：校验 X-API-Key，返回密钥。"""
    if not x_api_key:
        raise HTTPException(status_code=401, detail="缺少 X-API-Key 请求头")
    row = db.query_one(
        "SELECT id FROM api_keys WHERE key = ? AND revoked_at IS NULL", (x_api_key,)
    )
    if not row:
        raise HTTPException(status_code=403, detail="API Key 无效或已被吊销")
    return x_api_key
