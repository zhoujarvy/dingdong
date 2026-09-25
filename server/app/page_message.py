"""消息全文页：GET /m/{id}?token=xxx，免登录，打开即标记已读。"""
import html

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse

from . import db
from .utils import now_str, render_content

router = APIRouter()

PAGE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'%3E%3Cpath fill='%232f6fed' d='M12 2a6 6 0 0 0-6 6v3.6c0 .6-.24 1.18-.66 1.6L4 15.5h16l-1.34-1.9a2.4 2.4 0 0 1-.66-1.6V8a6 6 0 0 0-6-6z'/%3E%3Cpath fill='%232f6fed' d='M9.5 17a2.5 2.5 0 0 0 5 0z'/%3E%3C/svg%3E">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} - 叮咚</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: "Microsoft YaHei", "Segoe UI", sans-serif;
         background: #f0f2f5; color: #303133; min-height: 100vh; }}
  .card {{ max-width: 680px; margin: 32px auto; background: #fff; border-radius: 12px;
          box-shadow: 0 2px 12px rgba(0,0,0,.08); padding: 32px; }}
  .brand {{ color: #409eff; font-weight: 700; letter-spacing: 2px; margin-bottom: 20px; }}
  h1 {{ font-size: 22px; line-height: 1.5; margin-bottom: 12px; word-break: break-all; }}
  .meta {{ color: #909399; font-size: 13px; margin-bottom: 24px;
          padding-bottom: 16px; border-bottom: 1px solid #ebeef5; }}
  .meta span {{ margin-right: 16px; }}
  .content {{ font-size: 16px; line-height: 1.9; white-space: pre-wrap; word-break: break-word; }}
  .content a {{ color: #2f6fed; text-decoration: none; word-break: break-all; }}
  .content a:hover {{ text-decoration: underline; }}
  .footer {{ text-align: center; color: #c0c4cc; font-size: 12px; margin-top: 32px; }}
</style>
</head>
<body>
<div class="card">
  <div class="brand">叮咚</div>
  <h1>{title}</h1>
  <div class="meta">
    <span>发送方：{sender}</span>
    <span>推送时间：{created_at}</span>
  </div>
  <div class="content">{content}</div>
  <div class="footer">本页面由 叮咚消息推送系统 生成</div>
</div>
</body>
</html>"""

NOT_FOUND = """<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'%3E%3Cpath fill='%232f6fed' d='M12 2a6 6 0 0 0-6 6v3.6c0 .6-.24 1.18-.66 1.6L4 15.5h16l-1.34-1.9a2.4 2.4 0 0 1-.66-1.6V8a6 6 0 0 0-6-6z'/%3E%3Cpath fill='%232f6fed' d='M9.5 17a2.5 2.5 0 0 0 5 0z'/%3E%3C/svg%3E">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>消息不存在 - 叮咚</title>
<style>body{{font-family:"Microsoft YaHei",sans-serif;background:#f0f2f5;color:#909399;
display:flex;align-items:center;justify-content:center;min-height:100vh;font-size:15px;}}</style>
</head><body>消息不存在或访问令牌无效</body></html>"""


@router.get("/m/{message_id}", response_class=HTMLResponse)
def message_page(message_id: int, token: str = ""):
    row = db.query_one("SELECT * FROM messages WHERE id = ?", (message_id,))
    if not row or not token or token != row["access_token"]:
        return HTMLResponse(NOT_FOUND, status_code=404)

    # 打开全文页即视为已阅读
    if not row["read_at"]:
        db.execute(
            "UPDATE messages SET read_at = ? WHERE id = ? AND read_at IS NULL",
            (now_str(), message_id),
        )

    return PAGE.format(
        title=html.escape(row["title"] or ""),
        sender=html.escape(row["sender"] or "-"),
        created_at=html.escape(row["created_at"] or ""),
        content=render_content(row["content"] or "（无内容）"),
    )
