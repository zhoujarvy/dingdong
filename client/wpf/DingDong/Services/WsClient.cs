using System;
using System.Collections.Generic;
using System.Net.WebSockets;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using DingDong.Models;

namespace DingDong.Services
{
    /// <summary>与服务器的 WebSocket 长连接：自动重连、心跳、收发消息。</summary>
    public class WsClient : IDisposable
    {
        // 连接状态
        public const string StatusConnecting = "connecting";
        public const string StatusOnline = "online";
        public const string StatusOffline = "offline";
        public const string StatusRevoked = "revoked";      // 终端已注销，停止重连
        public const string StatusUnknown = "unknown";      // 终端不存在，停止重连

        /// <summary>UI 线程外触发的事件均已在内部调度回 UI 线程。</summary>
        public event Action<string> StatusChanged;
        public event Action<Message> MessageReceived;
        /// <summary>连接握手：携带 code/name/unread/inbox_token/inbox_url。</summary>
        public event Action<Dictionary<string, object>> HelloReceived;
        /// <summary>服务器同步的最新未读数（网页消息中心已读/删除后触发）。</summary>
        public event Action<int> UnreadChanged;

        private ClientWebSocket _ws;
        private Timer _heartbeatTimer;
        private CancellationTokenSource _cts;
        private volatile bool _stopped;
        private string _status;
        private readonly System.Windows.Threading.Dispatcher _ui;

        public string ServerUrl { get; set; }
        public string TerminalCode { get; set; }
        public string Status
        {
            get { return _status; }
            private set { _status = value; Raise(() => StatusChanged?.Invoke(value)); }
        }

        /// <param name="ui">UI 线程 Dispatcher，事件回调统一调度到该线程。</param>
        public WsClient(System.Windows.Threading.Dispatcher ui)
        {
            _ui = ui;
        }

        public void Start()
        {
            if (string.IsNullOrEmpty(ServerUrl) || string.IsNullOrEmpty(TerminalCode))
                return;
            _stopped = false;
            Task.Run(() => RunLoop());
        }

        public void Stop()
        {
            _stopped = true;
            try { _cts?.Cancel(); } catch { }
            try { if (_ws != null) _ws.Dispose(); } catch { }
            Status = StatusOffline;
        }

        /// <summary>重启（设置变更后调用）。</summary>
        public void Restart()
        {
            Stop();
            System.Threading.Thread.Sleep(200);
            Start();
        }

        private async void RunLoop()
        {
            int delay = 1000;
            while (!_stopped)
            {
                Status = StatusConnecting;
                _cts = new CancellationTokenSource();
                try
                {
                    var uri = new Uri(ServerUrl.TrimEnd('/')
                        .Replace("http://", "ws://").Replace("https://", "wss://")
                        + "/ws/" + Uri.EscapeDataString(TerminalCode));
                    _ws = new ClientWebSocket();
                    await _ws.ConnectAsync(uri, _cts.Token);
                    delay = 1000;
                    Status = StatusOnline;

                    StartHeartbeat();
                    await ReceiveLoop();
                }
                catch (OperationCanceledException) { }
                catch (Exception) { }
                finally
                {
                    StopHeartbeat();
                    if (_ws != null)
                    {
                        try { _ws.Dispose(); } catch { }
                        _ws = null;
                    }
                    if (!_stopped) Status = StatusOffline;
                }

                if (_stopped) return;
                // 断线退避重连：1s -> 2s -> 4s ... 最大 60s
                await Task.Delay(delay);
                delay = Math.Min(delay * 2, 60000);
            }
        }

        private async Task ReceiveLoop()
        {
            var buffer = new byte[64 * 1024];
            var sb = new StringBuilder();
            while (_ws != null && _ws.State == WebSocketState.Open && !_stopped)
            {
                WebSocketReceiveResult result;
                sb.Clear();
                do
                {
                    result = await _ws.ReceiveAsync(new ArraySegment<byte>(buffer), _cts.Token);
                    if (result.MessageType == WebSocketMessageType.Close)
                        await _ws.CloseAsync(WebSocketCloseStatus.NormalClosure, "close", CancellationToken.None);
                    sb.Append(Encoding.UTF8.GetString(buffer, 0, result.Count));
                } while (!result.EndOfMessage);

                if (result.CloseStatus != null) break;

                var text = sb.ToString();
                if (text.Length == 0) continue;
                HandleServerMessage(text);
            }
        }

        private void HandleServerMessage(string text)
        {
            Dictionary<string, object> msg = null;
            try { msg = Json.ParseObject(text); }
            catch { return; }
            if (msg == null || !msg.ContainsKey("type")) return;

            var type = Convert.ToString(msg["type"]);
            if (type == "hello")
            {
                var data = msg;
                Raise(() => HelloReceived?.Invoke(data));
            }
            else if (type == "unread")
            {
                int n = 0;
                object v;
                if (msg.TryGetValue("count", out v) && v != null)
                    int.TryParse(Convert.ToString(v), out n);
                Raise(() => UnreadChanged?.Invoke(n));
            }
            else if (type == "message")
            {
                var m = ParseMessage(msg["data"] as Dictionary<string, object>);
                if (m != null) Raise(() => MessageReceived?.Invoke(m));
            }
            else if (type == "rejected")
            {
                // 服务器拒绝：终端已注销或不存在，停止重连
                var reason = Convert.ToString(msg.ContainsKey("reason") ? msg["reason"] : "");
                _stopped = true;
                Status = reason == "revoked" ? StatusRevoked : StatusUnknown;
            }
            // heartbeat / messages 应答忽略
        }

        private static Message ParseMessage(Dictionary<string, object> d)
        {
            if (d == null) return null;
            return new Message
            {
                Id = Convert.ToInt32(d.ContainsKey("id") ? d["id"] : 0),
                Title = Convert.ToString(d.ContainsKey("title") ? d["title"] : "") ?? "",
                Content = Convert.ToString(d.ContainsKey("content") ? d["content"] : "") ?? "",
                Sender = Convert.ToString(d.ContainsKey("sender") ? d["sender"] : "") ?? "",
                Url = Convert.ToString(d.ContainsKey("url") ? d["url"] : "") ?? "",
                CreatedAt = Convert.ToString(d.ContainsKey("created_at") ? d["created_at"] : "") ?? "",
                PushedAt = Convert.ToString(d.ContainsKey("pushed_at") ? d["pushed_at"] : "") ?? "",
                Read = d.ContainsKey("read") && Convert.ToBoolean(d["read"]),
            };
        }

        private void StartHeartbeat()
        {
            StopHeartbeat();
            _heartbeatTimer = new Timer(async _ =>
            {
                try { await SendJson(new Dictionary<string, object> { { "type", "heartbeat" } }); }
                catch { }
            }, null, 30000, 30000);
        }

        private void StopHeartbeat()
        {
            if (_heartbeatTimer != null)
            {
                try { _heartbeatTimer.Dispose(); } catch { }
                _heartbeatTimer = null;
            }
        }

        private async Task SendJson(Dictionary<string, object> payload)
        {
            var ws = _ws;
            if (ws == null || ws.State != WebSocketState.Open) return;
            var bytes = Encoding.UTF8.GetBytes(Json.Serialize(payload));
            await ws.SendAsync(new ArraySegment<byte>(bytes), WebSocketMessageType.Text,
                true, _cts.Token);
        }

        private void Raise(Action action)
        {
            _ui.BeginInvoke(action);
        }

        public void Dispose()
        {
            Stop();
            _cts?.Dispose();
        }
    }
}
