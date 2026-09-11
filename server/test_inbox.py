"""消息中心与自助注销功能测试：hello 握手、时间分组接口、已读/删除/未读同步、注销。"""
import asyncio
import json
import time
import urllib.error
import urllib.request

BASE = "http://127.0.0.1:8000"


def http(method, path, body=None, headers=None):
    req = urllib.request.Request(BASE + path, method=method)
    req.add_header("Content-Type", "application/json")
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    data = json.dumps(body).encode() if body is not None else None
    with urllib.request.urlopen(req, data) as resp:
        return json.loads(resp.read().decode())


def push(headers, code, title, days_ago=None):
    """通过管理接口发消息；days_ago 用于构造历史时间。"""
    return http("POST", "/api/admin/push", {
        "terminal_codes": [code], "title": title, "content": "内容-" + title, "sender": "T",
    }, headers)


async def main():
    import websockets

    auth = http("POST", "/api/admin/login", {"password": "admin123"})
    H = {"Authorization": "Bearer " + auth["token"]}

    # 1. 注册终端（含 inbox_token）
    t = http("POST", "/api/terminals/register", {"name": "消息中心测试"})
    code, token = t["code"], t["inbox_token"]
    assert len(token) == 32, token
    print("[1] 注册终端 %s inbox_token=%s..." % (code, token[:8]))

    # 2. WS 连接收到 hello（含 unread/inbox_url/inbox_token）
    async with websockets.connect(f"ws://127.0.0.1:8000/ws/{code}") as ws:
        hello = json.loads(await ws.recv())
        assert hello["type"] == "hello" and hello["inbox_token"] == token
        assert hello["unread"] == 0 and code in hello["inbox_url"]
        print("[2] hello 握手 OK:", hello["inbox_url"])

        # 3. 推 3 条消息（1 在线 + 2 离线后再连）
        push(H, code, "在线消息A")
        m1 = json.loads(await ws.recv())
        assert m1["type"] == "message" and "&m=" in m1["data"]["url"]
        print("[3] 在线推送 url 指向消息中心 OK")

    push(H, code, "离线消息B")
    push(H, code, "离线消息C")

    # 4. 消息中心接口：首页 + 未读数
    data = http("GET", f"/api/inbox/{code}/messages?token={token}")
    assert len(data["items"]) == 3 and data["unread"] == 3 and data["has_more"] is False
    ids = [m["id"] for m in data["items"]]
    print("[4] 消息列表 3 条, 未读 3")

    # 5. 标记已读 -> WS 收到 unread 同步
    async with websockets.connect(f"ws://127.0.0.1:8000/ws/{code}") as ws:
        await ws.recv()  # hello
        # 消费补发的两条
        await ws.recv()
        await ws.recv()
        http("POST", f"/api/inbox/{code}/read/{ids[0]}?token={token}")
        while True:
            msg = json.loads(await ws.recv())
            if msg.get("type") == "unread":
                assert msg["count"] == 2
                break
        print("[5] 网页已读 -> 客户端 unread 同步 OK")

    # 6. 删除
    http("POST", f"/api/inbox/{code}/delete/{ids[2]}?token={token}")
    data = http("GET", f"/api/inbox/{code}/messages?token={token}")
    assert len(data["items"]) == 2
    print("[6] 网页删除 OK")

    # 7. 历史分页：再推 60 条，验证 has_more + before_id
    for i in range(60):
        push(H, code, f"批量-{i}")
    data = http("GET", f"/api/inbox/{code}/messages?token={token}&limit=50")
    assert len(data["items"]) == 50 and data["has_more"] is True
    oldest = data["items"][-1]["id"]
    page2 = http("GET", f"/api/inbox/{code}/messages?token={token}&before_id={oldest}")
    assert page2["has_more"] is False and len(page2["items"]) == 12
    print("[7] 历史分页 OK (第1页50条 + 第2页12条)")

    # 8. 页面 HTML 可访问
    with urllib.request.urlopen(f"{BASE}/t/{code}?token={token}") as r:
        page = r.read().decode()
    assert "消息中心" in page and code in page
    print("[8] 消息中心页面 OK")

    # 9. 错误 token 访问被拒
    try:
        http("GET", f"/api/inbox/{code}/messages?token=badtoken")
        raise AssertionError("bad token accepted")
    except urllib.error.HTTPError as e:
        assert e.code == 403
    print("[9] 错误令牌被拒 OK")

    # 10. 自助注销：正确凭据成功，注销后 WS 被拒
    r = http("POST", "/api/terminals/unregister", {"code": code, "token": token})
    assert r["ok"] is True
    ws2 = await websockets.connect(f"ws://127.0.0.1:8000/ws/{code}")
    rej = json.loads(await ws2.recv())
    assert rej == {"type": "rejected", "reason": "revoked"}
    await ws2.close()
    try:
        http("POST", "/api/terminals/unregister", {"code": code, "token": "0" * 32})
        raise AssertionError("wrong token accepted")
    except urllib.error.HTTPError as e:
        assert e.code == 403
    print("[10] 自助注销 + 注销后拒连 OK")

    print("\n=== 全部 10 项消息中心测试通过 ===")


asyncio.run(main())
