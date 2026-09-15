"""鉴权：管理后台会话 token（带角色）与第三方推送 API Key。

角色：
- admin：管理员，全部后台功能
- oper：操作员，仅允许登录后台并发送消息（/api/admin/push）
"""
import time
from typing import Optional

from fastapi import Depends, Header, HTTPException

from . import config, db
from .utils import gen_admin_token

# 内存会话：token -> (过期时间戳, 角色)（服务重启后需重新登录）
ADMIN_SESSIONS: dict = {}
SESSION_TTL = 12 * 3600


def create_session(role: str = "admin") -> str:
    token = gen_admin_token()
    ADMIN_SESSIONS[token] = (time.time() + SESSION_TTL, role)
    return token


def login_role(password: str) -> Optional[str]:
    """校验密码，返回命中的角色（admin/oper），失败返回 None。"""
    if password == config.get("admin_password"):
        return "admin"
    oper_pwd = config.get("oper_password")
    if oper_pwd and password == oper_pwd:
        return "oper"
    return None


def verify_password(password: str) -> bool:
    return login_role(password) is not None


def require_admin(authorization: str = Header(None)) -> str:
    """FastAPI 依赖：校验 Bearer token，返回角色。"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="未登录")
    token = authorization[7:].strip()
    session = ADMIN_SESSIONS.get(token)
    if session is None:
        raise HTTPException(status_code=401, detail="登录已失效")
    expire, role = session
    if time.time() > expire:
        ADMIN_SESSIONS.pop(token, None)
        raise HTTPException(status_code=401, detail="登录已过期")
    return role


def admin_only(role: str = Depends(require_admin)) -> str:
    """FastAPI 依赖：仅管理员可用（操作员 403）。"""
    if role != "admin":
        raise HTTPException(status_code=403, detail="需要管理员权限")
    return role


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
