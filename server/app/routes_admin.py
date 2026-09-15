"""管理后台 API：登录、总览、终端管理、消息记录、API 密钥、直接推送。"""
import math

from fastapi import APIRouter, Depends, HTTPException

from . import db, security
from .schemas import (
    AdminPushRequest,
    ApiKeyCreate,
    BatchDeleteRequest,
    LoginRequest,
    MessagePushRequest,
    TerminalCreateRequest,
)
from .utils import (
    days_ago_str,
    gen_access_token,
    gen_api_key,
    gen_terminal_code,
    now_str,
    today_start_str,
)
from .ws import kick_terminal, manager

router = APIRouter(prefix="/api/admin", dependencies=[Depends(security.require_admin)])
# 管理员专属路由：操作员（oper）登录后仅能访问 router 上的 /push
admin_router = APIRouter(
    prefix="/api/admin",
    dependencies=[Depends(security.require_admin), Depends(security.admin_only)],
)


# ---------- 登录（无需 token，单独挂载在 main） ----------
def login_route(req: LoginRequest):
    role = security.login_role(req.password)
    if role is None:
        raise HTTPException(status_code=401, detail="密码错误")
    return {"token": security.create_session(role), "role": role}


# ---------- 总览 ----------
@admin_router.get("/overview")
def overview():
    total = db.query_one("SELECT COUNT(*) AS c FROM terminals WHERE status='active'")["c"]
    online = len(manager.online_codes())
    today_msg = db.query_one(
        "SELECT COUNT(*) AS c FROM messages WHERE created_at >= ?", (today_start_str(),)
    )["c"]
    unread = db.query_one(
        "SELECT COUNT(*) AS c FROM messages WHERE read_at IS NULL AND deleted_at IS NULL"
    )["c"]
    pending = db.query_one(
        "SELECT COUNT(*) AS c FROM messages WHERE pushed_at IS NULL"
    )["c"]
    return {
        "terminals_active": total,
        "terminals_online": online,
        "messages_today": today_msg,
        "messages_unread": unread,
        "messages_pending": pending,
    }


# ---------- 终端管理 ----------
def _terminal_row(t: dict) -> dict:
    t = dict(t)
    t["online"] = manager.is_online(t["code"])
    return t


@admin_router.get("/terminals")
def list_terminals(status: str = "", page: int = 1, page_size: int = 20):
    where, params = "", []
    if status in ("active", "revoked"):
        where = "WHERE status = ?"
        params.append(status)
    total = db.query_one(f"SELECT COUNT(*) AS c FROM terminals {where}", tuple(params))["c"]
    rows = db.query(
        f"SELECT * FROM terminals {where} ORDER BY id DESC LIMIT ? OFFSET ?",
        tuple(params + [page_size, (page - 1) * page_size]),
    )
    return {"total": total, "pages": math.ceil(total / page_size) if page_size else 1,
            "items": [_terminal_row(r) for r in rows]}


@admin_router.post("/terminals")
def create_terminal(req: TerminalCreateRequest):
    code = None
    for _ in range(20):
        candidate = gen_terminal_code()
        if not db.query_one("SELECT id FROM terminals WHERE code = ?", (candidate,)):
            code = candidate
            break
    if code is None:
        raise HTTPException(500, "无法生成唯一编码")
    now = now_str()
    tid = db.execute(
        "INSERT INTO terminals (code, name, created_at, last_seen_at) VALUES (?,?,?,?)",
        (code, req.name, now, now),
    )
    return {"id": tid, "code": code, "name": req.name}


@admin_router.post("/terminals/{terminal_id}/revoke")
async def revoke_terminal(terminal_id: int):
    t = db.query_one("SELECT * FROM terminals WHERE id = ?", (terminal_id,))
    if not t:
        raise HTTPException(404, "终端不存在")
    if t["status"] == "active":
        db.execute(
            "UPDATE terminals SET status='revoked', revoked_at=?, revoke_reason='手动注销' WHERE id=?",
            (now_str(), terminal_id),
        )
        await kick_terminal(t["code"])
    return {"ok": True}


@admin_router.post("/terminals/{terminal_id}/restore")
async def restore_terminal(terminal_id: int):
    t = db.query_one("SELECT * FROM terminals WHERE id = ?", (terminal_id,))
    if not t:
        raise HTTPException(404, "终端不存在")
    db.execute(
        "UPDATE terminals SET status='active', revoked_at=NULL, revoke_reason=NULL, "
        "last_seen_at=? WHERE id=?",
        (now_str(), terminal_id),
    )
    return {"ok": True}


# ---------- 消息记录 ----------
@admin_router.get("/messages")
def list_messages(terminal_id: int = 0, read: str = "", page: int = 1, page_size: int = 20):
    where, params = ["1=1"], []
    if terminal_id:
        where.append("m.terminal_id = ?")
        params.append(terminal_id)
    if read == "unread":
        where.append("m.read_at IS NULL")
    elif read == "read":
        where.append("m.read_at IS NOT NULL")
    cond = " AND ".join(where)

    total = db.query_one(
        f"SELECT COUNT(*) AS c FROM messages m WHERE {cond}", tuple(params))["c"]
    rows = db.query(
        f"SELECT m.*, t.code AS terminal_code, t.name AS terminal_name "
        f"FROM messages m JOIN terminals t ON t.id = m.terminal_id "
        f"WHERE {cond} ORDER BY m.id DESC LIMIT ? OFFSET ?",
        tuple(params + [page_size, (page - 1) * page_size]),
    )
    return {"total": total, "pages": math.ceil(total / page_size) if page_size else 1,
            "items": rows}


@admin_router.post("/messages/batch-delete")
def batch_delete_messages(req: BatchDeleteRequest):
    """管理员批量删除消息（物理删除，不可恢复）。"""
    q = ",".join("?" * len(req.ids))
    conn = db._conn()
    cur = conn.execute(f"DELETE FROM messages WHERE id IN ({q})", tuple(req.ids))
    conn.commit()
    return {"deleted": cur.rowcount}


# ---------- API 密钥 ----------
@admin_router.get("/apikeys")
def list_apikeys():
    rows = db.query(
        "SELECT * FROM api_keys ORDER BY id DESC"
    )
    for r in rows:
        r["revoked"] = r["revoked_at"] is not None
    return {"items": rows}


@admin_router.post("/apikeys")
def create_apikey(req: ApiKeyCreate):
    kid = db.execute(
        "INSERT INTO api_keys (name, key, created_at) VALUES (?,?,?)",
        (req.name, gen_api_key(), now_str()),
    )
    return db.query_one("SELECT * FROM api_keys WHERE id = ?", (kid,))


@admin_router.post("/apikeys/{key_id}/revoke")
def revoke_apikey(key_id: int):
    k = db.query_one("SELECT * FROM api_keys WHERE id = ?", (key_id,))
    if not k:
        raise HTTPException(404, "密钥不存在")
    if not k["revoked_at"]:
        db.execute(
            "UPDATE api_keys SET revoked_at=? WHERE id=?", (now_str(), key_id)
        )
    return {"ok": True}


# ---------- 直接推送（后台测试发送，复用推送逻辑） ----------
@router.post("/push")
async def admin_push(req: AdminPushRequest):
    push_req = MessagePushRequest(
        terminal_codes=req.terminal_codes,
        title=req.title,
        content=req.content,
        sender=req.sender,
    )
    from .routes_public import push_messages
    return await push_messages(push_req, None)
