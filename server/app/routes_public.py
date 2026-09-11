"""公共接口：终端注册（客户端调用）、消息推送（第三方调用，需 API Key）。"""
import logging

from fastapi import APIRouter, Depends, HTTPException

from . import db
from .schemas import (
    MessagePushRequest,
    PushResponse,
    PushResultItem,
    RegisterRequest,
    TerminalInfo,
    UnregisterRequest,
)
from .security import require_api_key
from .utils import gen_access_token, gen_terminal_code, now_str
from .ws import deliver_message, kick_terminal

log = logging.getLogger("dingdong.api")

router = APIRouter(prefix="/api")


@router.post("/terminals/register", response_model=TerminalInfo)
def register_terminal(req: RegisterRequest):
    """客户端注册终端：提交名称，返回唯一 6 位编码。"""
    code = None
    for _ in range(20):  # 冲突重试
        candidate = gen_terminal_code()
        if not db.query_one("SELECT id FROM terminals WHERE code = ?", (candidate,)):
            code = candidate
            break
    if code is None:  # 理论上几乎不可能
        raise RuntimeError("无法生成唯一终端编码，请重试")

    now = now_str()
    tid = db.execute(
        "INSERT INTO terminals (code, name, created_at, last_seen_at, inbox_token) "
        "VALUES (?,?,?,?,?)",
        (code, req.name, now, now, gen_access_token()),
    )
    log.info("新终端注册: %s -> %s", req.name, code)
    row = db.query_one("SELECT * FROM terminals WHERE id = ?", (tid,))
    return TerminalInfo(code=code, name=req.name, inbox_token=row["inbox_token"])


@router.post("/messages", response_model=PushResponse)
async def push_messages(req: MessagePushRequest, _: str = Depends(require_api_key)):
    """第三方推送消息：支持单发（terminal_code）与群发（terminal_codes）。"""
    codes = req.target_codes()
    if not codes:
        raise HTTPException(status_code=400, detail="未指定接收终端编码")

    results = []
    delivered = 0
    for code in codes:
        terminal = db.query_one("SELECT * FROM terminals WHERE code = ?", (code,))
        if not terminal or terminal["status"] != "active":
            results.append(PushResultItem(
                terminal_code=code,
                error="终端不存在或已注销",
            ))
            continue

        mid = db.execute(
            "INSERT INTO messages (terminal_id, title, content, sender, access_token, created_at) "
            "VALUES (?,?,?,?,?,?)",
            (terminal["id"], req.title, req.content, req.sender,
             gen_access_token(), now_str()),
        )
        ok = await deliver_message(mid, terminal)
        delivered += 1 if ok else 0
        results.append(PushResultItem(
            terminal_code=code, message_id=mid, delivered=ok,
            error=None if ok else "终端不在线，已入库等待补发",
        ))

    return PushResponse(total=len(results), delivered=delivered, results=results)


@router.post("/terminals/unregister")
async def unregister_terminal(req: UnregisterRequest):
    """客户端自助注销：凭终端编码 + 消息中心令牌注销，注销后可重新注册。"""
    terminal = db.query_one("SELECT * FROM terminals WHERE code = ?", (req.code.strip().upper(),))
    if not terminal or not req.token or req.token != terminal["inbox_token"]:
        raise HTTPException(status_code=403, detail="终端编码或令牌错误")
    if terminal["status"] == "active":
        db.execute(
            "UPDATE terminals SET status='revoked', revoked_at=?, revoke_reason=? WHERE id=?",
            (now_str(), "客户端主动注销", terminal["id"]),
        )
        await kick_terminal(terminal["code"])
        log.info("终端自助注销: %s(%s)", terminal["name"], terminal["code"])
    return {"ok": True}


@router.get("/health")
def health():
    return {"status": "ok", "service": "dingdong"}
