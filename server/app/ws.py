"""WebSocket 长连接：实时推送、心跳、离线补发、已读/删除上报、网页消息中心联动。"""
import asyncio
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from . import db
from .utils import now_str

log = logging.getLogger("dingdong.ws")

router = APIRouter()

# WebSocket 关闭代码（客户端据此区分状态）
CLOSE_TERMINAL_NOT_FOUND = 4404
CLOSE_TERMINAL_REVOKED = 4403

INBOX_LIMIT = 200  # 客户端/消息中心拉取列表的最大条数


class ConnectionManager:
    """同一终端允许多条连接并存（多台电脑同时登录同一编码，各自收到推送）。"""

    def __init__(self):
        self.active: dict = {}  # code -> list[WebSocket]
        self.lock = asyncio.Lock()

    async def connect(self, code: str, ws: WebSocket) -> None:
        async with self.lock:
            conns = self.active.setdefault(code, [])
            if ws not in conns:
                conns.append(ws)

    async def disconnect(self, code: str, ws: WebSocket) -> None:
        async with self.lock:
            conns = self.active.get(code)
            if conns and ws in conns:
                conns.remove(ws)
                if not conns:
                    del self.active[code]

    def is_online(self, code: str) -> bool:
        return bool(self.active.get(code))

    def online_codes(self) -> list:
        return list(self.active.keys())

    async def send_to_terminal(self, code: str, payload: dict) -> bool:
        """向该终端的所有在线连接广播 JSON，至少送达一条即返回 True。"""
        conns = list(self.active.get(code) or [])
        if not conns:
            return False
        delivered = False
        for ws in conns:
            try:
                await ws.send_json(payload)
                delivered = True
            except Exception:
                await self.disconnect(code, ws)
        return delivered


manager = ConnectionManager()


def unread_count(terminal_id: int) -> int:
    return db.query_one(
        "SELECT COUNT(*) AS c FROM messages "
        "WHERE terminal_id = ? AND read_at IS NULL AND deleted_at IS NULL",
        (terminal_id,),
    )["c"]


async def push_unread(terminal: dict) -> None:
    """向在线终端同步最新未读数（网页消息中心已读/删除后调用）。"""
    await manager.send_to_terminal(
        terminal["code"], {"type": "unread", "count": unread_count(terminal["id"])}
    )


def _message_payload(row: dict, terminal: dict) -> dict:
    inbox = "/t/{}?token={}&m={}".format(terminal["code"], terminal["inbox_token"], row["id"])
    return {
        "type": "message",
        "data": {
            "id": row["id"],
            "title": row["title"],
            "content": row["content"],
            "sender": row["sender"],
            "url": inbox,  # 点击弹窗打开网页消息中心并定位到该消息
            "created_at": row["created_at"],
            "pushed_at": row.get("pushed_at"),
            "read": row.get("read_at") is not None,
        },
    }


async def deliver_message(message_id: int, terminal: dict) -> bool:
    """推送一条已入库的消息给在线终端，送达后记录 pushed_at。"""
    row = db.query_one("SELECT * FROM messages WHERE id = ?", (message_id,))
    if not row:
        return False
    ok = await manager.send_to_terminal(terminal["code"], _message_payload(row, terminal))
    if ok:
        db.execute(
            "UPDATE messages SET pushed_at = ? WHERE id = ? AND pushed_at IS NULL",
            (now_str(), message_id),
        )
    return ok


async def deliver_pending(terminal: dict) -> None:
    """连接后仅补发「尚未推送过」的消息（未读/已读过的历史由网页消息中心查看）。"""
    rows = db.query(
        "SELECT * FROM messages WHERE terminal_id = ? AND deleted_at IS NULL "
        "AND pushed_at IS NULL ORDER BY id ASC",
        (terminal["id"],),
    )
    for row in rows:
        db.execute(
            "UPDATE messages SET pushed_at = ? WHERE id = ? AND pushed_at IS NULL",
            (now_str(), row["id"]),
        )
        try:
            await manager.send_to_terminal(terminal["code"], _message_payload(row, terminal))
        except Exception:
            break


@router.websocket("/ws/{code}")
async def terminal_ws(ws: WebSocket, code: str):
    terminal = db.query_one(
        "SELECT * FROM terminals WHERE code = ?", (code.strip().upper(),)
    )
    if not terminal:
        await ws.accept()
        await ws.send_json({"type": "rejected", "reason": "not_found"})
        await ws.close(code=CLOSE_TERMINAL_NOT_FOUND, reason="终端不存在")
        return
    if terminal["status"] != "active":
        await ws.accept()
        await ws.send_json({"type": "rejected", "reason": "revoked"})
        await ws.close(code=CLOSE_TERMINAL_REVOKED, reason="终端已注销")
        return

    await ws.accept()
    await manager.connect(code, ws)
    db.execute(
        "UPDATE terminals SET last_seen_at = ? WHERE id = ?", (now_str(), terminal["id"])
    )
    log.info("终端上线 %s(%s) 在线数=%d", terminal["name"], code, len(manager.active))

    try:
        # 握手：告知消息中心地址与当前未读数
        await ws.send_json({
            "type": "hello",
            "code": terminal["code"],
            "name": terminal["name"],
            "unread": unread_count(terminal["id"]),
            "inbox_url": "/t/{}?token={}".format(terminal["code"], terminal["inbox_token"]),
            "inbox_token": terminal["inbox_token"],
        })
        await deliver_pending(terminal)

        while True:
            msg = await ws.receive_json()
            mtype = msg.get("type")

            if mtype == "heartbeat":
                db.execute(
                    "UPDATE terminals SET last_seen_at = ? WHERE id = ?",
                    (now_str(), terminal["id"]),
                )
                await ws.send_json({"type": "heartbeat", "server_time": now_str()})

            elif mtype == "list":
                rows = db.query(
                    "SELECT * FROM messages WHERE terminal_id = ? AND deleted_at IS NULL "
                    "ORDER BY id DESC LIMIT ?",
                    (terminal["id"], INBOX_LIMIT),
                )
                items = [_message_payload(r, terminal)["data"] for r in rows]
                await ws.send_json({"type": "messages", "items": items})

            elif mtype == "read":
                mid = msg.get("message_id")
                db.execute(
                    "UPDATE messages SET read_at = ? "
                    "WHERE id = ? AND terminal_id = ? AND read_at IS NULL",
                    (now_str(), mid, terminal["id"]),
                )
                await push_unread(terminal)

            elif mtype == "delete":
                mid = msg.get("message_id")
                db.execute(
                    "UPDATE messages SET deleted_at = ? "
                    "WHERE id = ? AND terminal_id = ? AND deleted_at IS NULL",
                    (now_str(), mid, terminal["id"]),
                )
                await push_unread(terminal)
    except WebSocketDisconnect:
        pass
    except Exception:
        log.exception("终端连接异常 %s", code)
    finally:
        await manager.disconnect(code, ws)
        db.execute(
            "UPDATE terminals SET last_seen_at = ? WHERE id = ?",
            (now_str(), terminal["id"]),
        )
        log.info("终端下线 %s(%s) 在线数=%d", terminal["name"], code, len(manager.active))


async def kick_terminal(code: str) -> None:
    """注销终端时断开其全部连接。"""
    for ws in list(manager.active.get(code) or []):
        try:
            await ws.close(code=CLOSE_TERMINAL_REVOKED, reason="终端已注销")
        except Exception:
            pass
        await manager.disconnect(code, ws)
