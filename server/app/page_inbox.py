"""网页消息中心：/t/{code}?token=xxx —— 主视图按时间分组（今天/昨天/近3天/近7天，可折叠），
更早消息通过「历史记录」入口分页查看；点击查看全文并标记已读、删除、自动刷新。
页面 JS 采用 ES5 + XMLHttpRequest，兼容旧浏览器。"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse

from . import db
from .utils import now_str
from .ws import push_unread

router = APIRouter()

PAGE_SIZE = 50  # 每页条数（可翻页加载历史）


def _terminal_or_403(code: str, token: str) -> dict:
    terminal = db.query_one(
        "SELECT * FROM terminals WHERE code = ?", (code.strip().upper(),)
    )
    if not terminal or not token or token != terminal["inbox_token"]:
        raise HTTPException(status_code=403, detail="终端不存在或令牌无效")
    return terminal


# ---------- HTML 页面 ----------
@router.get("/t/{code}", response_class=HTMLResponse)
def inbox_page(code: str, token: str = ""):
    terminal = db.query_one(
        "SELECT * FROM terminals WHERE code = ?", (code.strip().upper(),)
    )
    if not terminal or not token or token != terminal["inbox_token"]:
        return HTMLResponse(PAGE_FORBIDDEN, status_code=403)
    revoked = terminal["status"] != "active"
    return (PAGE_HTML
            .replace("__CODE__", terminal["code"])
            .replace("__NAME__", terminal["name"].replace("&", "&amp;").replace("<", "&lt;"))
            .replace("__REVOKED__", "true" if revoked else "false"))


# ---------- JSON 接口（页面 JS 调用） ----------
@router.get("/api/inbox/{code}/messages")
def inbox_messages(code: str, token: str = "", before_id: int = 0, limit: int = PAGE_SIZE):
    terminal = _terminal_or_403(code, token)
    limit = max(1, min(limit, 100))
    if before_id > 0:
        rows = db.query(
            "SELECT id, title, content, sender, created_at, pushed_at, read_at "
            "FROM messages WHERE terminal_id = ? AND deleted_at IS NULL AND id < ? "
            "ORDER BY id DESC LIMIT ?",
            (terminal["id"], before_id, limit + 1),
        )
    else:
        rows = db.query(
            "SELECT id, title, content, sender, created_at, pushed_at, read_at "
            "FROM messages WHERE terminal_id = ? AND deleted_at IS NULL "
            "ORDER BY id DESC LIMIT ?",
            (terminal["id"], limit + 1),
        )
    has_more = len(rows) > limit
    rows = rows[:limit]
    unread = db.query_one(
        "SELECT COUNT(*) AS c FROM messages "
        "WHERE terminal_id = ? AND read_at IS NULL AND deleted_at IS NULL",
        (terminal["id"],),
    )["c"]
    return JSONResponse({
        "items": rows,
        "unread": unread,
        "has_more": has_more,
        "revoked": terminal["status"] != "active",
    })


@router.post("/api/inbox/{code}/read/{message_id}")
async def inbox_read(code: str, message_id: int, token: str = ""):
    terminal = _terminal_or_403(code, token)
    db.execute(
        "UPDATE messages SET read_at = ? "
        "WHERE id = ? AND terminal_id = ? AND read_at IS NULL",
        (now_str(), message_id, terminal["id"]),
    )
    await push_unread(terminal)  # 同步客户端托盘未读角标
    return {"ok": True}


@router.post("/api/inbox/{code}/delete/{message_id}")
async def inbox_delete(code: str, message_id: int, token: str = ""):
    terminal = _terminal_or_403(code, token)
    db.execute(
        "UPDATE messages SET deleted_at = ? "
        "WHERE id = ? AND terminal_id = ? AND deleted_at IS NULL",
        (now_str(), message_id, terminal["id"]),
    )
    await push_unread(terminal)
    return {"ok": True}


# ---------- 页面模板 ----------
PAGE_HTML = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'%3E%3Cpath fill='%232f6fed' d='M12 2a6 6 0 0 0-6 6v3.6c0 .6-.24 1.18-.66 1.6L4 15.5h16l-1.34-1.9a2.4 2.4 0 0 1-.66-1.6V8a6 6 0 0 0-6-6z'/%3E%3Cpath fill='%232f6fed' d='M9.5 17a2.5 2.5 0 0 0 5 0z'/%3E%3C/svg%3E">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="X-UA-Compatible" content="IE=edge">
<title>消息中心 - 叮咚</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: "Microsoft YaHei","Segoe UI",sans-serif; background:#f4f6f9; color:#26303b;
         -webkit-font-smoothing: antialiased; }
  .wrap { max-width: 680px; margin: 0 auto; padding: 22px 16px 48px; }

  /* 顶栏 */
  .head { padding: 4px 2px 16px; }
  .head .row1 { display: flex; align-items: baseline; }
  .head .brand { font-size: 19px; font-weight: 700; letter-spacing: 1px; color:#26303b; }
  .head .brand #modeName::before { content: " · "; color:#c2c9d4; }
  .head .term { color:#7d8894; font-size: 12.5px; margin-left: auto; letter-spacing: .5px; }
  .head .row2 { margin-top: 12px; display: flex; align-items: center; }
  .head .unread { background:#2f6fed; color:#fff; border-radius: 999px;
                  font-size: 12px; padding: 3px 12px; letter-spacing: .5px; }
  .head .toggle { color:#9aa4b0; font-size: 12.5px; cursor: pointer; border: none;
                  background: none; padding: 2px 0; margin-left: auto; }
  .head .toggle:hover { color:#2f6fed; }

  .banner { display:none; background:#fff7e9; color:#b26a00; border-radius:10px;
            font-size:13px; padding:10px 14px; margin-bottom:12px; }
  .banner.show { display:block; }

  /* 分组面板 */
  .group { background:#fff; border-radius:14px; margin-bottom:14px; overflow:hidden;
           box-shadow: 0 1px 3px rgba(38,48,59,.06); }
  .group .gbar { display:flex; align-items:center; padding:14px 18px; cursor:pointer;
                 user-select:none; }
  .group.open .gbar { border-bottom: 1px solid #f0f2f5; }
  .group .gbar .arr { display:inline-block; width:0; height:0; border-left:5px solid #c2c9d4;
                      border-top:4px solid transparent; border-bottom:4px solid transparent;
                      margin-right:11px; transition: transform .2s; }
  .group.open .gbar .arr { transform: rotate(90deg); border-left-color:#2f6fed; }
  .group .gbar .gname { font-size:14.5px; font-weight:600; letter-spacing:.5px; }
  .group .gbar .gcount { font-size:12px; color:#9aa4b0; margin-left:10px;
                         background:#f1f3f7; border-radius:999px; padding:1px 9px; }
  .group .gbar .gunread { font-size:12px; color:#2f6fed; margin-left:6px;
                          background:#eaf1fe; border-radius:999px; padding:1px 9px; }
  .group .gbody { display:none; }
  .group.open .gbody { display:block; }

  /* 消息行 */
  .card { border-bottom:1px solid #f0f2f5; }
  .group .gbody .card:last-child { border-bottom:none; }
  .card .bar { padding:13px 18px 12px 16px; cursor:pointer; position:relative; }
  .card .bar:hover { background:#f8fafc; }
  .dot { display:inline-block; width:8px; height:8px; border-radius:50%; background:#2f6fed;
         margin-right:9px; vertical-align:2px; flex:none;
         box-shadow: 0 0 0 3px rgba(47,111,237,.16); }
  .dot.read { background:#cfd5dd; box-shadow:none; }
  .bar .title { font-size:15px; font-weight:600; word-break:break-all; line-height:1.5; }
  .bar .title.read { font-weight:400; color:#68727e; }
  .bar .meta { font-size:12px; color:#8a95a1; margin-top:4px; }
  .bar .tag { font-size:11px; color:#7d8894; border-radius:999px; padding:1px 8px;
              margin-left:8px; background:#f1f3f7; }
  .bar .tag.unread { color:#2f6fed; background:#eaf1fe; }
  .del { position:absolute; right:14px; top:10px; border:none; background:none; color:#98a2ae;
         font-size:14px; cursor:pointer; padding:4px 6px; font-family:Arial;
         opacity:.6; transition: all .18s; }
  .card .bar:hover .del { opacity:1; }
  .del:hover { color:#e5484d; }
  .body { display:none; margin:0 18px 14px 32px; padding:12px 14px; font-size:14.5px;
          line-height:1.85; white-space:pre-wrap; word-break:break-word;
          background:#f7f9fb; border-radius:10px; color:#3b4550; }
  .card.open .body { display:block; }
  .body a { color:#2f6fed; text-decoration:none; word-break:break-all; }
  .body a:hover { text-decoration:underline; }
  .card.hl { background:#f3f8ff; }
  .card.hl .bar { background:transparent; }
  .card.open.hl { background:#fff; }

  /* 历史记录 */
  .flat { margin-top:2px; background:#fff; border-radius:14px; overflow:hidden;
          box-shadow: 0 1px 3px rgba(38,48,59,.06); }
  .flat .card:last-child { border-bottom:none; }
  .action { display:block; width:100%; background:#fff; border:1px solid #e4e8ee;
            border-radius:12px; color:#2f6fed; font-size:13.5px; padding:13px;
            cursor:pointer; margin-top:14px; transition: all .18s; letter-spacing:1px; }
  .action:hover { border-color:#2f6fed; }
  .action.plain { color:#7a8694; margin-top:12px; }
  .action.plain:hover { color:#2f6fed; border-color:#2f6fed; }
  .back { display:inline-block; color:#2f6fed; font-size:13.5px; cursor:pointer;
          padding:2px 0 4px; margin-bottom:8px; }
  .empty { text-align:center; color:#9aa4b0; font-size:14px; padding:56px 0; }
  .footer { text-align:center; color:#c2c9d4; font-size:12px; padding-top:18px; }
</style>
</head>
<body>
<div class="wrap">
  <div class="head">
    <div class="row1">
      <span class="brand">&#128276; 叮咚<span id="modeName">消息中心</span></span>
      <span class="term">__CODE__ &middot; __NAME__</span>
    </div>
    <div class="row2" id="mainTools">
      <span class="unread" id="unreadBadge" style="display:none"></span>
      <button class="toggle" id="toggleAll" type="button">全部收起</button>
    </div>
  </div>
  <div class="banner" id="revokedBanner">该终端已注销，不再接收新消息，历史消息仅供查阅。</div>
  <a class="back" id="backLink" href="javascript:void(0)" style="display:none">&laquo; 返回消息中心</a>
  <div id="list"></div>
  <button class="action plain" id="historyBtn" type="button"
          style="display:none">查看历史记录 &raquo;</button>
  <div id="historyBox" style="display:none"></div>
  <div class="empty" id="empty" style="display:none">近 7 天内暂无消息</div>
  <div class="footer" id="footTip">点击消息展开查看全文并标记已读 · 每 15 秒自动刷新</div>
</div>
<script>
(function () {
  var CODE = "__CODE__";
  var TOKEN = getParam("token");
  var targetId = parseInt(getParam("m"), 10) || 0;
  var revoked = __REVOKED__ === true;

  var historyMode = getParam("history") === "1";
  var all = [];            // 主视图已加载消息（id 降序）
  var hist = [];           // 历史记录已加载消息（id 降序）
  var histHasMore = false;
  var mainHasMore = false;
  var unread = 0;
  var collapsed = { "d3": true, "d7": true };  // 今天/昨天默认展开
  var openIds = {};        // 展开的消息卡片
  var GROUPS = [
    { key: "today", name: "今天" },
    { key: "yesterday", name: "昨天" },
    { key: "d3", name: "近 3 天" },
    { key: "d7", name: "近 7 天" }
  ];
  var loadMoreBtn = null;

  function getParam(name) {
    var qs = location.search.substring(1).split("&");
    for (var i = 0; i < qs.length; i++) {
      var kv = qs[i].split("=");
      if (decodeURIComponent(kv[0]) === name) return decodeURIComponent((kv[1] || "").replace(/\\+/g, " "));
    }
    return "";
  }

  function xhr(method, url, onOk) {
    var x = new XMLHttpRequest();
    x.open(method, url, true);
    x.onreadystatechange = function () {
      if (x.readyState !== 4) return;
      if (x.status >= 200 && x.status < 300) {
        try { onOk(JSON.parse(x.responseText)); } catch (e) {}
      }
    };
    x.send();
  }

  // 依据 created_at（YYYY-MM-DD HH:MM:SS，服务器本地时间）计算分组；older=超7天
  function groupKey(m) {
    var p = (m.created_at || "").split(" ")[0].split("-");
    if (p.length !== 3) return "older";
    var d = new Date(parseInt(p[0], 10), parseInt(p[1], 10) - 1, parseInt(p[2], 10));
    if (isNaN(d.getTime())) return "older";
    var today = new Date();
    today.setHours(0, 0, 0, 0);
    var days = Math.floor((today.getTime() - d.getTime()) / 86400000);
    if (days <= 0) return "today";
    if (days === 1) return "yesterday";
    if (days <= 3) return "d3";
    if (days <= 7) return "d7";
    return "older";
  }

  function setUnread(n) {
    unread = n;
    var badge = document.getElementById("unreadBadge");
    badge.style.display = unread > 0 ? "" : "none";
    badge.innerHTML = unread + " 条未读";
    if (!historyMode) {
      document.title = (unread > 0 ? "(" + unread + ") " : "") + "消息中心 - 叮咚";
    }
  }

  // ---------- 主视图：分组渲染 ----------
  function renderMain() {
    var list = document.getElementById("list");
    list.innerHTML = "";
    var i, g, m;
    var recent = [];
    for (i = 0; i < all.length; i++) if (groupKey(all[i]) !== "older") recent.push(all[i]);

    document.getElementById("empty").style.display = recent.length ? "none" : "block";
    var anyOpen = false;

    var buckets = {};
    for (i = 0; i < GROUPS.length; i++) buckets[GROUPS[i].key] = [];
    for (i = 0; i < recent.length; i++) buckets[groupKey(recent[i])].push(recent[i]);

    // 弹窗定位进来的消息：自动展开其所在分组
    if (targetId) {
      for (i = 0; i < all.length; i++) {
        if (all[i].id === targetId) { collapsed[groupKey(all[i])] = false; break; }
      }
    }

    for (var gi = 0; gi < GROUPS.length; gi++) {
      g = GROUPS[gi];
      var items = buckets[g.key];
      if (!items.length) continue;

      var grp = document.createElement("div");
      var isOpen = !collapsed[g.key];
      grp.className = isOpen ? "group open" : "group";
      anyOpen = anyOpen || isOpen;

      var gbar = document.createElement("div");
      gbar.className = "gbar";
      var gUnread = 0;
      for (i = 0; i < items.length; i++) if (!items[i].read_at) gUnread++;
      gbar.innerHTML = '<span class="arr"></span><span class="gname">' + g.name + "</span>" +
        '<span class="gcount">' + items.length + " 条</span>" +
        (gUnread > 0 ? '<span class="gunread">未读 ' + gUnread + "</span>" : "");
      gbar.onclick = (function (key) {
        return function () { collapsed[key] = !collapsed[key]; renderMain(); };
      })(g.key);

      var gbody = document.createElement("div");
      gbody.className = "gbody";
      for (i = 0; i < items.length; i++) gbody.appendChild(buildCard(items[i]));
      grp.appendChild(gbar);
      grp.appendChild(gbody);
      list.appendChild(grp);
    }
    document.getElementById("toggleAll").innerHTML = anyOpen ? "全部收起" : "全部展开";
    if (revoked) document.getElementById("revokedBanner").className = "banner show";
  }

  // ---------- 历史记录视图：平铺分页 ----------
  function renderHistory() {
    var box = document.getElementById("historyBox");
    box.innerHTML = "";
    for (var i = 0; i < hist.length; i++) box.appendChild(buildCard(hist[i]));
    if (histHasMore) {
      var more = document.createElement("button");
      more.className = "action";
      more.type = "button";
      more.innerHTML = "加载更早的消息";
      more.onclick = function () { loadHistory(hist.length ? hist[hist.length - 1].id : 0); };
      box.appendChild(more);
    } else if (!hist.length) {
      var e = document.createElement("div");
      e.className = "empty";
      e.innerHTML = "暂无历史消息";
      box.appendChild(e);
    }
  }

  // 正文填充：URL（http/https）转为新窗口打开的链接，其余为纯文本节点（防 XSS）
  function fillBody(el, text) {
    var s = text || "";
    var re = /(https?:\/\/[^\s<>"']+)/ig, m, last = 0;
    el.innerHTML = "";
    while ((m = re.exec(s)) !== null) {
      if (m.index > last) el.appendChild(document.createTextNode(s.substring(last, m.index)));
      var a = document.createElement("a");
      a.href = m[1];
      a.target = "_blank";
      a.rel = "noopener";
      a.appendChild(document.createTextNode(m[1]));
      el.appendChild(a);
      last = m.index + m[1].length;
    }
    if (last < s.length) el.appendChild(document.createTextNode(s.substring(last)));
    if (!el.firstChild) el.appendChild(document.createTextNode("（无内容）"));
  }

  function buildCard(m) {
    var read = !!m.read_at;
    var card = document.createElement("div");
    card.className = "card" + (openIds[m.id] ? " open" : "");

    var bar = document.createElement("div");
    bar.className = "bar";
    var del = document.createElement("button");
    del.className = "del";
    del.type = "button";
    del.title = "删除";
    del.innerHTML = '<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path></svg>';
    del.onclick = function (ev) {
      (ev.stopPropagation ? ev.stopPropagation() : (ev.cancelBubble = true));
      if (!confirm("确定删除这条消息？")) return;
      xhr("POST", "/api/inbox/" + CODE + "/delete/" + m.id + "?token=" + TOKEN, function () {
        if (historyMode) loadHistory(0); else loadMain();
      });
    };

    var dot = document.createElement("span");
    dot.className = "dot" + (read ? " read" : "");
    var title = document.createElement("span");
    title.className = "title" + (read ? " read" : "");
    title.appendChild(document.createTextNode(m.title || ""));
    var meta = document.createElement("div");
    meta.className = "meta";
    meta.appendChild(document.createTextNode((m.sender || "-") + " · " + (m.created_at || "")));
    var tag = document.createElement("span");
    tag.className = "tag" + (read ? "" : " unread");
    tag.innerHTML = read ? "已读" : "未读";
    meta.appendChild(tag);

    bar.appendChild(del);
    bar.appendChild(dot);
    bar.appendChild(title);
    bar.appendChild(meta);

    var body = document.createElement("div");
    body.className = "body";
    fillBody(body, m.content);

    bar.onclick = function () {
      var opening = card.className.indexOf("open") < 0;
      if (opening) {
        card.className += " open";
        openIds[m.id] = true;
      } else {
        card.className = card.className.replace(/\\s*open/, "");
        openIds[m.id] = false;
      }
      if (opening && !read) {
        read = true;
        dot.className = "dot read";
        title.className = "title read";
        tag.className = "tag";
        tag.innerHTML = "已读";
        m.read_at = m.read_at || "1";
        setUnread(unread > 0 ? unread - 1 : 0);
        if (!historyMode) renderMain();
        xhr("POST", "/api/inbox/" + CODE + "/read/" + m.id + "?token=" + TOKEN, null);
      }
    };

    card.appendChild(bar);
    card.appendChild(body);

    // 目标消息（弹窗点进来的）：自动展开、高亮、滚动定位并标记已读
    if (m.id === targetId) {
      if (!openIds[m.id]) { openIds[m.id] = true; card.className += " open hl"; }
      else { card.className += " hl"; }
      if (!read) {
        m.read_at = m.read_at || "1";
        setUnread(unread > 0 ? unread - 1 : 0);
        xhr("POST", "/api/inbox/" + CODE + "/read/" + m.id + "?token=" + TOKEN, null);
      }
      setTimeout(function () {
        if (card.scrollIntoView) card.scrollIntoView(true);
        window.scrollBy(0, -80);
      }, 150);
    }
    return card;
  }

  // ---------- 数据加载 ----------
  function loadMain() {
    xhr("GET", "/api/inbox/" + CODE + "/messages?token=" + TOKEN + "&limit=50", function (data) {
      var items = data.items || [];
      setUnread(data.unread || 0);
      mainHasMore = !!data.has_more;

      // 合并刷新：保留展开状态；第一页窗口内消失的消息视为已删除
      var map = {}, i;
      for (i = 0; i < all.length; i++) map[all[i].id] = all[i];
      var fresh = {};
      for (i = 0; i < items.length; i++) { fresh[items[i].id] = true; map[items[i].id] = items[i]; }
      var minId = items.length ? items[items.length - 1].id : 0;
      var merged = [];
      for (var idStr in map) {
        var idNum = parseInt(idStr, 10);
        if (!fresh[idNum] && idNum >= minId) continue;  // 已被删除
        merged.push(map[idStr]);
      }
      merged.sort(function (a, b) { return b.id - a.id; });
      all = merged;

      // 目标消息若不属于近 7 天（或未在首页加载到），自动转入历史记录查找
      var target = targetId ? findById(all, targetId) : null;
      if (targetId && (!target || groupKey(target) === "older") &&
          (mainHasMore || hasOlder(all))) {
        switchToHistory(true);
        return;
      }
      renderMain();
    });
  }

  function hasOlder(arr) {
    for (var i = 0; i < arr.length; i++) if (groupKey(arr[i]) === "older") return true;
    return false;
  }

  function findById(arr, id) {
    for (var i = 0; i < arr.length; i++) if (arr[i].id === id) return arr[i];
    return null;
  }

  function loadHistory(before) {
    var url = "/api/inbox/" + CODE + "/messages?token=" + TOKEN + "&limit=50";
    if (before > 0) url += "&before_id=" + before;
    xhr("GET", url, function (data) {
      var items = data.items || [];
      setUnread(data.unread || 0);
      histHasMore = !!data.has_more;
      if (before > 0) {
        for (var i = 0; i < items.length; i++) hist.push(items[i]);
        renderHistory();
      } else {
        hist = items;
        renderHistory();
      }
      // 弹窗定位的目标消息可能在更早的页，自动翻页查找（最多 20 页）
      if (targetId && !findById(hist, targetId) && histHasMore && autoSeek < 20) {
        autoSeek++;
        loadHistory(hist[hist.length - 1].id);
      }
    });
  }

  var autoSeek = 0;

  function switchToHistory(seek) {
    historyMode = true;
    autoSeek = seek ? 1 : 0;
    document.getElementById("modeName").innerHTML = "历史记录";
    document.title = "历史记录 - 叮咚";
    document.getElementById("mainTools").style.display = "none";
    document.getElementById("historyBtn").style.display = "none";
    document.getElementById("list").innerHTML = "";
    document.getElementById("empty").style.display = "none";
    document.getElementById("footTip").innerHTML = "历史消息按时间倒序排列";
    var back = document.getElementById("backLink");
    back.style.display = "";
    back.onclick = function () {
      location.href = "/t/" + CODE + "?token=" + encodeURIComponent(TOKEN);
    };
    document.getElementById("historyBox").style.display = "";
    loadHistory(0);
  }

  // ---------- 初始化 ----------
  document.getElementById("toggleAll").onclick = function () {
    var anyOpen = false, i;
    for (i = 0; i < GROUPS.length; i++) if (!collapsed[GROUPS[i].key]) anyOpen = true;
    for (i = 0; i < GROUPS.length; i++) collapsed[GROUPS[i].key] = anyOpen;
    renderMain();
  };

  var historyBtn = document.getElementById("historyBtn");
  historyBtn.onclick = function () {
    location.href = "/t/" + CODE + "?token=" + encodeURIComponent(TOKEN) + "&history=1";
  };

  if (historyMode) {
    switchToHistory(false);
  } else {
    historyBtn.style.display = "";
    loadMain();
    setInterval(function () { if (!historyMode) loadMain(); }, 15000);
  }
})();
</script>
</body>
</html>"""

PAGE_FORBIDDEN = """<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'%3E%3Cpath fill='%232f6fed' d='M12 2a6 6 0 0 0-6 6v3.6c0 .6-.24 1.18-.66 1.6L4 15.5h16l-1.34-1.9a2.4 2.4 0 0 1-.66-1.6V8a6 6 0 0 0-6-6z'/%3E%3Cpath fill='%232f6fed' d='M9.5 17a2.5 2.5 0 0 0 5 0z'/%3E%3C/svg%3E">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>消息中心 - 叮咚</title>
<style>body{font-family:"Microsoft YaHei",sans-serif;background:#f0f2f5;color:#909399;
display:flex;align-items:center;justify-content:center;min-height:100vh;font-size:15px;}</style>
</head><body>消息中心访问令牌无效，请从客户端重新打开。</body></html>"""
