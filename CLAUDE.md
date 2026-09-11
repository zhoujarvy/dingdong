# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目简介

叮咚（DingDong）：自托管消息推送系统。第三方程序经 HTTP 接口投递消息 → FastAPI 服务端入库 → WebSocket 实时推送到 Windows 托盘客户端（提示音/TTS/弹窗）→ 用户在网页消息中心查看、已读、删除。生产环境为内网部署。

## 常用命令

```bash
# 服务端（Python 3.8 + FastAPI + uvicorn + SQLite）
cd server && pip install -r requirements.txt
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000   # 或 start.bat

# 管理后台（Vue 3 + Element Plus + Vite）
cd web && npm install
npm run dev      # 开发模式 http://localhost:5173（/api、/ws 代理到 127.0.0.1:8000）
npm run build    # 构建产物输出到 server/static（emptyOutDir），由服务端托管

# 客户端（C# WPF，.NET 6 自包含单文件发布，目标机免装运行时）
cd client && make_installer.bat   # dotnet publish → Inno Setup → server/downloads/DingDongSetup.exe + version.txt
dotnet publish DingDong/DingDong.csproj -c Release    # 仅编译，产物约 66MB 单文件 exe

# 测试（服务端）
cd server && python test_e2e.py    # 端到端测试
cd server && python test_inbox.py  # 收件箱分页测试
```

## 架构

三个模块，关键数据流：

- **server/**（FastAPI，单进程）
  - `app/main.py`：应用入口与路由挂载。官网 `site.html` 与管理后台 `index.html` 均在 `web/` 开发，`npm run build` 一并输出到 `server/static`；`/` 服务端返回 site.html，`/admin/{rest}` 回退 SPA index.html、`/download/{filename}` 客户端安装包分发
  - `app/routes_public.py`：第三方推送 API（`X-API-Key` 认证）+ 网页消息中心/消息全文页的匿名 JSON API（token 认证）
  - `app/routes_admin.py`：管理后台 API（密码认证，配置在 `server/config.json` 的 `admin_password`）
  - `app/ws.py`：核心 `ConnectionManager`（code → WebSocket 字典，同码重连踢旧连接 close 4400）。协议为**双向 JSON**：服务端推 `hello`/`messages`/`data`，客户端发 `list`/心跳/已读/删除上报
  - `app/page_inbox.py`、`app/page_message.py`：**纯 Python 字符串模板**渲染的网页消息中心与消息全文页（非前端框架），修改页面即改这两个文件
  - `app/db.py`：SQLite（WAL 模式），`server/dingdong.db`；含 `auto_revoke_loop`（30 天未连接自动注销终端）
- **web/**：Vue 3 管理后台源码（views: Overview/Messages/Terminals/ApiKeys/Push 等），vite outDir 直接指向 `server/static`
- **client/**：WPF + WinForms 托盘（`MainWindow.xaml.cs` 的 `InitTray`），Services 下有 WsClient/ApiClient/TtsService(System.Speech)/NotifyManager/SettingsStore。**.NET 6 self-contained 单文件**，必须保持 Win7 SP1 兼容（这是选 net6 而非 net8 的原因），安装为当前用户模式（PrivilegesRequired=lowest）

## 重要约定

- 消息生命周期：`created_at` → `pushed_at`（WS 送达）→ `read_at`；客户端删除为**软删除**，管理后台保留审计
- 终端不在线时消息入库，上线后补发（正序逐条标记 pushed_at）
- WebSocket 关闭码：4400 同码顶替、4403 终端已注销、4404 终端不存在
- 修改客户端发布/打包配置在 `DingDong.csproj` 与 `installer/DingDong.iss`，两者需同步（发布路径 `bin/Release/net6.0-windows/win-x64/publish/`）
- 完整协议、数据库表结构、全量 API 见 `docs/系统技术文档.md`；第三方接入示例见 `docs/第三方接入文档.md`
- 生产部署（Nginx + NSSM）见 `deploy/部署说明.md`
