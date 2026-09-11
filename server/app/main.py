"""叮咚服务端入口：路由挂载、静态托管、终端超时自动注销任务。"""
import asyncio
import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from . import config, db
from .routes_admin import login_route, router as admin_router
from .routes_public import router as public_router
from .page_message import router as page_router
from .page_inbox import router as inbox_router
from .schemas import LoginRequest
from .ws import kick_terminal, router as ws_router
from .utils import days_ago_str, now_str

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)
log = logging.getLogger("dingdong")

app = FastAPI(title="叮咚 DingDong", docs_url="/api/docs", openapi_url="/api/openapi.json")

# 开发期允许 Vite 开发服务器跨域访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(public_router)
app.include_router(admin_router)
app.include_router(page_router)
app.include_router(inbox_router)
app.include_router(ws_router)


@app.post("/api/admin/login")
def admin_login(req: LoginRequest):
    return login_route(req)


# ---------- 终端超时自动注销 ----------
async def auto_revoke_loop():
    while True:
        try:
            cutoff = days_ago_str(int(config.get("terminal_offline_days")))
            rows = db.query(
                "SELECT code FROM terminals WHERE status='active' AND last_seen_at < ?",
                (cutoff,),
            )
            for r in rows:
                db.execute(
                    "UPDATE terminals SET status='revoked', revoked_at=?, revoke_reason=? "
                    "WHERE code=? AND status='active'",
                    (now_str(), "超过30天未连接，自动注销", r["code"]),
                )
                await kick_terminal(r["code"])
                log.info("终端 %s 超过期限未连接，已自动注销", r["code"])
        except Exception:
            log.exception("自动注销任务执行失败")
        await asyncio.sleep(3600)


@app.on_event("startup")
async def on_startup():
    db.init_db()
    asyncio.create_task(auto_revoke_loop())
    log.info("叮咚服务端已启动，数据库: %s", config.db_path())


# ---------- 静态资源：官网（/）、管理后台（/admin）、下载 ----------
# 官网（site.html）与管理后台（index.html）均在 web/ 中开发，npm run build 一并输出到 static/
STATIC_DIR = os.path.join(config.BASE_DIR, "static")
DOWNLOADS_DIR = os.path.join(config.BASE_DIR, "downloads")  # 客户端安装包等下载物
ASSETS_DIR = os.path.join(STATIC_DIR, "assets")

if os.path.isdir(ASSETS_DIR):
    app.mount("/assets", StaticFiles(directory=ASSETS_DIR), name="assets")


def _file(dir_path: str, name: str):
    path = os.path.join(dir_path, name)
    return FileResponse(path) if os.path.exists(path) else None


@app.get("/api/download/info")
def download_info():
    """官网展示的客户端安装包信息。"""
    import datetime

    exe = os.path.join(DOWNLOADS_DIR, "DingDongSetup.exe")
    if not os.path.exists(exe):
        return {"available": False}
    size = os.path.getsize(exe)
    mtime = datetime.datetime.fromtimestamp(os.path.getmtime(exe))
    version = ""
    vfile = os.path.join(DOWNLOADS_DIR, "version.txt")
    if os.path.exists(vfile):
        try:
            version = open(vfile, encoding="ascii").read().strip()
        except OSError:
            pass
    return {
        "available": True,
        "filename": "DingDongSetup.exe",
        "version": version,
        "size_text": "%.1f MB" % (size / 1048576),
        "updated_at": mtime.strftime("%Y-%m-%d %H:%M"),
    }


@app.get("/download/{filename}")
def download_file(filename: str):
    if filename == "dingdong-api-doc.md":
        path = os.path.join(config.BASE_DIR, "..", "docs", "第三方接入文档.md")
        path = os.path.normpath(path)
        if os.path.exists(path):
            return FileResponse(path, filename="叮咚消息推送系统-第三方接入文档.md")
        return HTMLResponse("文档尚未生成", status_code=404)
    safe = os.path.normpath(os.path.join(DOWNLOADS_DIR, filename))
    if safe.startswith(DOWNLOADS_DIR) and os.path.isfile(safe):
        return FileResponse(safe)
    return HTMLResponse("文件不存在", status_code=404)


@app.get("/", response_class=HTMLResponse)
def site_index():
    page = _file(STATIC_DIR, "site.html")
    if page:
        return page
    admin = _file(STATIC_DIR, "index.html")
    if admin:
        return admin
    return HTMLResponse("<h3>叮咚服务端运行中</h3><p>接口文档：<a href='/api/docs'>/api/docs</a></p>")


@app.get("/admin", response_class=HTMLResponse)
@app.get("/admin/{rest:path}", response_class=HTMLResponse)
def admin_index(rest: str = ""):
    """管理后台（隐蔽入口：官网页脚邮戳 / 直接访问 /admin）。"""
    page = _file(STATIC_DIR, "index.html")
    if page:
        return page
    return HTMLResponse(
        "<h3>管理后台尚未构建</h3><p>请在 web/ 目录执行 <code>npm install && npm run build</code></p>"
    )


@app.get("/{full_path:path}", response_class=HTMLResponse)
def spa_fallback(full_path: str):
    """其余 GET 请求回落到静态文件 / 官网首页。"""
    if full_path.startswith(("api/", "ws/", "m/", "t/", "assets/", "download/")):
        return HTMLResponse("Not Found", status_code=404)
    candidate = os.path.normpath(os.path.join(STATIC_DIR, full_path))
    if candidate.startswith(STATIC_DIR) and os.path.isfile(candidate):
        return FileResponse(candidate)
    page = _file(STATIC_DIR, "site.html")
    if page:
        return page
    path = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(path):
        return FileResponse(path)
    return HTMLResponse("Not Found", status_code=404)
