# 叮咚 (DingDong)

通用消息推送系统：第三方程序通过 HTTP 接口推送消息，Windows 客户端驻留系统托盘实时接收（提示音 / TTS 朗读 / 右下角弹窗），点击弹窗打开**网页消息中心**查看全文。

- **官网**：服务启动后访问 `http://服务器IP:8000/`——系统介绍、客户端下载、使用教程与接口文档（`web/site.html`，随管理后台一起构建）
- **管理后台**：`http://服务器IP:8000/admin`（官网页脚的邮戳即隐蔽入口），密码在 `server/config.json`
- 客户端仅负责接收提醒（托盘未读角标 + 弹窗），消息的查看 / 已读 / 删除统一在网页消息中心进行，按今天 / 昨天 / 近 3 天 / 近 7 天分组折叠，更早消息走「历史记录」分页查询
- 文档：**[docs/系统技术文档.md](docs/系统技术文档.md)**（架构/数据库/协议/全量 API，面向维护者）、**[docs/第三方接入文档.md](docs/第三方接入文档.md)**（面向第三方调用方，含 curl / Python / C# / JS 示例，也可从官网下载）
- **生产部署**（Nginx + NSSM）参考 **[deploy/部署说明.md](deploy/部署说明.md)**

## 组成

| 模块 | 技术栈 | 说明 |
|------|--------|------|
| `server/` | FastAPI + SQLite + WebSocket | 消息接收/推送/离线补发、终端管理、管理后台 API、消息全文页 |
| `web/` | Vue 3 + Element Plus + Vite | 管理后台源码，构建产物输出到 `server/static` 由服务端托管 |
| `client/` | C# WPF (.NET 6 自包含) | Windows 托盘客户端，支持 Win7 SP1 / Win10，免装运行时 |

## 快速开始（服务端）

```bash
cd server
pip install -r requirements.txt
start.bat          # 或: python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

- 管理后台: http://服务器IP:8000/ （默认密码在 `server/config.json` 的 `admin_password`，首次部署请修改）
- 配置文件: `server/config.json`

## 快速开始（客户端）

两种方式任选：

- **推荐**：从官网 `http://服务器IP:8000/` 下载 `DingDongSetup.exe` 安装包（Inno Setup 制作，安装到当前用户目录，无需管理员权限；.NET 运行时已内嵌，免安装）
- 开发调试：用 Visual Studio 2019/2022（或 `dotnet build`）编译 `client/DingDong.sln`，Release 输出 `DingDong.exe`

运行后填写服务器地址（如 `http://192.168.1.10:8000`）和终端名称，点击注册，获得 6 位终端编码。

### 客户端打包（生成分发安装包）

```bat
cd client
make_installer.bat
```

一键完成「编译 → Inno Setup 打包 → 输出到 `server/downloads/DingDongSetup.exe` → 写入版本号 version.txt（官网下载区自动展示版本/大小/日期）」。需要本机安装 [Inno Setup 6](https://jrsoftware.org/isinfo.php)。

客户端为 .NET 6 自包含发布，运行时已打包在安装包内，目标机器无需任何额外安装。

## 第三方推送接口

先在管理后台「API 密钥」页创建密钥，然后：

```bash
curl -X POST http://服务器IP:8000/api/messages \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dd_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx" \
  -d '{
    "terminal_code": "A2B3C4",
    "title": "测试消息",
    "content": "这是消息内容，支持多行文本。",
    "sender": "业务系统"
  }'
```

- `terminal_code` 可换成 `terminal_codes`（数组）实现群发，详见接入文档
- 终端不在线时消息入库，上线后自动补发
- 终端超过 30 天未连接服务器将自动注销，客户端也可在设置中主动注销后重新注册

## 消息生命周期

- `created_at`：接口收到消息的时间
- `pushed_at`：消息经 WebSocket 送达客户端的时间
- `read_at`：用户点击弹窗/列表打开全文页的时间
- 客户端删除为软删除，管理后台仍可查历史记录

## 目录内联调

```bash
# 服务端
cd server && python -m uvicorn app.main:app --port 8000

# 管理后台开发模式（热更新）
cd web && npm install && npm run dev   # http://localhost:5173

# 前端构建（产物自动写入 server/static，由服务端托管）
cd web && npm run build
```
