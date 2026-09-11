"""叮咚端到端流程测试：注册 -> 管理登录 -> 建密钥 -> 推送 -> WS 收件 -> 已读/删除 -> 全文页。"""
import asyncio
import json
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


async def main():
    import websockets

    # 1. 注册终端
    t = http("POST", "/api/terminals/register", {"name": "测试终端"})
    code = t["code"]
    assert len(code) == 6 and code.isalnum() and code.isupper(), code
    print("[1] 注册终端:", code)

    # 2. 管理登录 + 建 API 密钥
    login = http("POST", "/api/admin/login", {"password": "admin123"})
    auth = {"Authorization": "Bearer " + login["token"]}
    key = http("POST", "/api/admin/apikeys", {"name": "测试系统"}, auth)
    api_key = key["key"]
    print("[2] API Key:", api_key)

    # 3. 推送消息（终端离线，应入库待补发）
    push = http("POST", "/api/messages", {
        "terminal_code": code,
        "title": "测试标题「引号&特殊<>字符」",
        "content": "第一行内容\n第二行内容",
        "sender": "E2E",
    }, {"X-API-Key": api_key})
    assert push["results"][0]["message_id"] and not push["results"][0]["delivered"]
    mid = push["results"][0]["message_id"]
    print("[3] 离线推送入库, message_id =", mid)

    # 4. WS 连接：先收到 hello 握手，再收到补发消息
    async with websockets.connect(f"ws://127.0.0.1:8000/ws/{code}") as ws:
        hello = json.loads(await ws.recv())
        assert hello["type"] == "hello" and hello["inbox_token"], hello
        first = json.loads(await ws.recv())
        assert first["type"] == "message", first
        data = first["data"]
        assert data["id"] == mid and data["title"].startswith("测试标题")
        url = data["url"]
        print("[4] WS 补发收到:", data["title"], "url =", url)

        # 5. 请求列表
        await ws.send(json.dumps({"type": "list"}))
        lst = json.loads(await ws.recv())
        assert lst["type"] == "messages" and len(lst["items"]) == 1
        print("[5] 列表条数: 1")

        # 6. 实时推送（在线）
        push2 = http("POST", "/api/messages", {
            "terminal_code": code, "title": "在线消息", "content": "hi", "sender": "E2E",
        }, {"X-API-Key": api_key})
        assert push2["results"][0]["delivered"] is True
        live = json.loads(await ws.recv())
        assert live["type"] == "message" and live["data"]["title"] == "在线消息"
        print("[6] 在线实时送达 OK")

        # 7. 标记已读 + 删除第一条
        await ws.send(json.dumps({"type": "read", "message_id": mid}))
        await ws.send(json.dumps({"type": "delete", "message_id": mid}))
        await asyncio.sleep(0.3)
        print("[7] 已读+删除上报 OK")

        url = None  # url 已改为消息中心链接，全文页改用 access_token 验证

        # 8. 心跳（已读/删除的 unread 同步可能插在前面，循环消费）
        await ws.send(json.dumps({"type": "heartbeat"}))
        for _ in range(5):
            hb = json.loads(await ws.recv())
            if hb["type"] == "heartbeat":
                break
        assert hb["type"] == "heartbeat"
        print("[8] 心跳 OK")

    # 9. 全文页（带 access_token 打开即已读）与已读/删除校验
    msgs = http("GET", "/api/admin/messages?terminal_id=0", None, auth)
    items = {m["id"]: m for m in msgs["items"]}
    page = urllib.request.urlopen(
        BASE + "/m/{}?token={}".format(mid, items[mid]["access_token"])).read().decode()
    assert "测试标题" in page and "第一行内容" in page
    assert items[mid]["read_at"] and items[mid]["deleted_at"], items[mid]
    m2 = [m for m in msgs["items"] if m["title"] == "在线消息"][0]
    assert m2["pushed_at"] and not m2["deleted_at"]
    print("[9] 全文页/状态校验 OK")

    # 10. 错误密钥应被拒绝
    try:
        http("POST", "/api/messages", {"terminal_code": code, "title": "x"}, {"X-API-Key": "dd_bad"})
        raise AssertionError("bad key accepted!")
    except urllib.error.HTTPError as e:
        assert e.code == 403
    print("[10] 错误密钥被拒绝 OK")

    # 11. 已注销终端 WS 应被拒
    terms = http("GET", "/api/admin/terminals", None, auth)["items"]
    tid = [t["id"] for t in terms if t["code"] == code][0]
    http("POST", f"/api/admin/terminals/{tid}/revoke", {}, auth)
    ws2 = await websockets.connect(f"ws://127.0.0.1:8000/ws/{code}")
    rej = json.loads(await ws2.recv())
    assert rej == {"type": "rejected", "reason": "revoked"}, rej
    await ws2.close()
    print("[11] 注销终端被拒绝 OK")

    print("\n=== 全部 11 项端到端测试通过 ===")


asyncio.run(main())
