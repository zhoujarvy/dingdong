using System;
using System.Diagnostics;
using System.Drawing;
using System.Drawing.Drawing2D;
using System.Runtime.InteropServices;
using System.Windows;
using System.Windows.Controls;
using WinForms = System.Windows.Forms;
using DingDong.Models;
using DingDong.Services;

namespace DingDong
{
    /// <summary>
    /// 主窗口：注册向导 + 终端状态 + 设置。消息的查看/已读/删除统一在网页消息中心进行，
    /// 客户端仅负责接收提醒（提示音 / TTS / 弹窗）并在托盘图标上显示未读数。
    /// </summary>
    public partial class MainWindow : Window
    {
        private readonly Settings _settings;
        private WsClient _ws;
        private WinForms.NotifyIcon _tray;
        private System.Drawing.Icon _trayIcon;
        private bool _reallyExit;
        private int _unread;

        public MainWindow(Settings settings, bool startMinimized)
        {
            InitializeComponent();
            _settings = settings;

            NotifyManager.Init(this);

            if (_settings.Registered)
            {
                ShowMainPanel();
                if (startMinimized)
                {
                    // 静默启动：不显示窗口，但需强制创建句柄以初始化托盘与连接
                    new System.Windows.Interop.WindowInteropHelper(this).EnsureHandle();
                }
                else
                {
                    Show();
                }
            }
            else
            {
                TxtServerUrl.Text = string.IsNullOrEmpty(_settings.ServerUrl) ? "http://" : _settings.ServerUrl;
                RegisterPanel.Visibility = Visibility.Visible;
                MainPanel.Visibility = Visibility.Collapsed;
                Show();
            }

            Closing += (s, e) =>
            {
                if (_reallyExit || !_settings.Registered) return;
                e.Cancel = true;   // 已注册时关闭窗口仅隐藏到托盘
                Hide();
            };
        }

        protected override void OnSourceInitialized(EventArgs e)
        {
            base.OnSourceInitialized(e);
            InitTray();
            if (_settings.Registered) StartWs();
        }

        // ================= 注册 =================
        private async void BtnRegister_Click(object sender, RoutedEventArgs e) => await RegisterAsync();

        private async void TxtTerminalName_KeyDown(object sender, System.Windows.Input.KeyEventArgs e)
        {
            if (e.Key == System.Windows.Input.Key.Enter) await RegisterAsync();
        }

        private async System.Threading.Tasks.Task RegisterAsync()
        {
            var server = TxtServerUrl.Text.Trim().TrimEnd('/');
            var name = TxtTerminalName.Text.Trim();
            if (!server.StartsWith("http")) { TbRegisterTip.Text = "服务器地址需以 http:// 开头"; return; }
            if (name.Length == 0) { TbRegisterTip.Text = "请输入终端名称"; return; }

            BtnRegister.IsEnabled = false;
            TbRegisterTip.Text = "正在注册…";
            try
            {
                var result = await System.Threading.Tasks.Task.Run(
                    () => ApiClient.Register(server, name));
                _settings.ServerUrl = server;
                _settings.TerminalCode = Convert.ToString(result["code"]);
                _settings.TerminalName = Convert.ToString(result["name"]);
                _settings.InboxToken = Convert.ToString(result["inbox_token"]);
                SettingsStore.Save(_settings);
                _unread = 0;
                ShowMainPanel();
                StartWs();
            }
            catch (Exception ex)
            {
                TbRegisterTip.Text = "注册失败：" + ex.Message;
            }
            finally
            {
                BtnRegister.IsEnabled = true;
            }
        }

        private void ShowMainPanel()
        {
            RegisterPanel.Visibility = Visibility.Collapsed;
            MainPanel.Visibility = Visibility.Visible;
            TbCode.Text = _settings.TerminalCode;
            TbTerminalName.Text = _settings.TerminalName;
            UpdateUnread();

            // 载入设置
            TxtSettingsServer.Text = _settings.ServerUrl;
            ChkSound.IsChecked = _settings.SoundEnabled;
            ChkTts.IsChecked = _settings.TtsEnabled;
            CmbTtsMode.SelectedIndex = _settings.TtsMode == "both" ? 1 : 0;
            ChkAutoStart.IsChecked = _settings.AutoStart;
        }

        // ================= 连接 =================
        private void StartWs()
        {
            if (_ws != null) { _ws.Dispose(); }

            _ws = new WsClient(Dispatcher)
            {
                ServerUrl = _settings.ServerUrl,
                TerminalCode = _settings.TerminalCode,
            };
            _ws.StatusChanged += OnStatusChanged;
            _ws.HelloReceived += OnHello;
            _ws.UnreadChanged += OnUnreadChanged;
            _ws.MessageReceived += OnMessageReceived;
            _ws.Start();
        }

        private void OnStatusChanged(string status)
        {
            string text;
            System.Windows.Media.Brush color;
            switch (status)
            {
                case WsClient.StatusOnline:
                    text = "已连接"; color = System.Windows.Media.Brushes.Green; break;
                case WsClient.StatusConnecting:
                    text = "连接中…"; color = System.Windows.Media.Brushes.Orange; break;
                case WsClient.StatusRevoked:
                    text = "终端已注销"; color = System.Windows.Media.Brushes.Red;
                    HandleRevoked(); break;
                case WsClient.StatusUnknown:
                    text = "终端不存在"; color = System.Windows.Media.Brushes.Red;
                    HandleRevoked(); break;
                default:
                    text = "已断开，自动重连中"; color = System.Windows.Media.Brushes.Gray; break;
            }
            TbStatus.Text = text;
            StatusDot.Fill = color;
            UpdateTrayTooltip();
        }

        private void OnHello(System.Collections.Generic.Dictionary<string, object> hello)
        {
            // 服务器握手：同步消息中心令牌与未读数（令牌可能已轮换，落盘持久化）
            var token = Convert.ToString(hello.ContainsKey("inbox_token") ? hello["inbox_token"] : "");
            if (!string.IsNullOrEmpty(token) && token != _settings.InboxToken)
            {
                _settings.InboxToken = token;
                SettingsStore.Save(_settings);
            }
            OnUnreadChanged(Json.GetInt(hello, "unread", _unread));
        }

        private void OnUnreadChanged(int count)
        {
            _unread = count;
            UpdateUnread();
        }

        private void HandleRevoked()
        {
            var tip = _ws != null && _ws.Status == WsClient.StatusRevoked
                ? "该终端已注销（超过一个月未连接、被管理员注销或已在别处注销），需要重新注册。"
                : "该终端编码在服务器上不存在，需要重新注册。";
            MessageBox.Show(this, tip, "叮咚", MessageBoxButton.OK, MessageBoxImage.Warning);
            BackToRegisterPanel();
        }

        private void BackToRegisterPanel()
        {
            SettingsStore.Reset(_settings);
            _unread = 0;
            UpdateUnread();
            if (_ws != null) { _ws.Dispose(); _ws = null; }
            TxtServerUrl.Text = string.IsNullOrEmpty(_settings.ServerUrl) ? "http://" : _settings.ServerUrl;
            TxtTerminalName.Clear();
            RegisterPanel.Visibility = Visibility.Visible;
            MainPanel.Visibility = Visibility.Collapsed;
            Show();
            Activate();
        }

        // ================= 消息提醒 =================
        private void OnMessageReceived(Message msg)
        {
            if (!msg.Read)
            {
                _unread++;
                UpdateUnread();
            }
            NotifyManager.Notify(msg, _settings);
        }

        // ================= 消息中心 =================
        private string InboxUrl(string messageId = null)
        {
            var url = _settings.ServerUrl.TrimEnd('/') + "/t/" + Uri.EscapeDataString(_settings.TerminalCode)
                      + "?token=" + Uri.EscapeDataString(_settings.InboxToken);
            if (!string.IsNullOrEmpty(messageId)) url += "&m=" + messageId;
            return url;
        }

        private void OpenInbox(string messageId = null)
        {
            if (!_settings.Registered || string.IsNullOrEmpty(_settings.InboxToken))
            {
                MessageBox.Show(this, "尚未注册或未连接服务器，暂时无法打开消息中心。", "叮咚");
                return;
            }
            try { Browser.Open(InboxUrl(messageId)); }
            catch (Exception ex) { MessageBox.Show("打开网页失败：" + ex.Message, "叮咚"); }
        }

        private void BtnOpenInbox_Click(object sender, RoutedEventArgs e) => OpenInbox();

        private void BtnCopyCode_Click(object sender, RoutedEventArgs e)
        {
            try { Clipboard.SetText(_settings.TerminalCode); }
            catch { }
        }

        // ================= 设置 =================
        private void BtnSaveSettings_Click(object sender, RoutedEventArgs e)
        {
            _settings.SoundEnabled = ChkSound.IsChecked == true;
            _settings.TtsEnabled = ChkTts.IsChecked == true;
            _settings.TtsMode = (CmbTtsMode.SelectedItem as ComboBoxItem)?.Tag as string ?? "title";
            var autoStart = ChkAutoStart.IsChecked == true;
            _settings.AutoStart = autoStart;
            SetAutoStart(autoStart);

            var newServer = TxtSettingsServer.Text.Trim().TrimEnd('/');
            var serverChanged = newServer != _settings.ServerUrl && newServer.StartsWith("http");
            if (serverChanged) _settings.ServerUrl = newServer;
            SettingsStore.Save(_settings);

            if (serverChanged && _ws != null)
            {
                _ws.ServerUrl = _settings.ServerUrl;
                _ws.Restart();
            }
            MessageBox.Show(this, "设置已保存", "叮咚", MessageBoxButton.OK, MessageBoxImage.Information);
        }

        private async void BtnUnregister_Click(object sender, RoutedEventArgs e)
        {
            if (MessageBox.Show(this, "确定注销此终端？注销后将不再接收消息，需要重新注册。",
                    "叮咚", MessageBoxButton.OKCancel, MessageBoxImage.Question) != MessageBoxResult.OK)
                return;

            // 通知服务器注销（失败不阻断：本地照常重置，服务器侧终端超时后也会自动注销）
            try
            {
                var server = _settings.ServerUrl;
                var code = _settings.TerminalCode;
                var token = _settings.InboxToken;
                if (!string.IsNullOrEmpty(token))
                    await System.Threading.Tasks.Task.Run(() => ApiClient.Unregister(server, code, token));
            }
            catch (Exception ex)
            {
                MessageBox.Show(this, "服务器注销失败（" + ex.Message + "），已仅清除本地信息。",
                    "叮咚", MessageBoxButton.OK, MessageBoxImage.Warning);
            }
            BackToRegisterPanel();
        }

        private void SetAutoStart(bool enable)
        {
            try
            {
                var key = Microsoft.Win32.Registry.CurrentUser.CreateSubKey(
                    @"Software\Microsoft\Windows\CurrentVersion\Run");
                if (enable)
                {
                    var exe = Process.GetCurrentProcess().MainModule.FileName;
                    key.SetValue("DingDong", "\"" + exe + "\" --minimized");
                }
                else
                {
                    key.DeleteValue("DingDong", false);
                }
            }
            catch { }
        }

        // ================= 托盘 =================
        private void InitTray()
        {
            _tray = new WinForms.NotifyIcon
            {
                Visible = true,
                Text = "叮咚",
            };
            _trayIcon = BuildIcon(0);
            _tray.Icon = _trayIcon;
            UpdateTrayTooltip();

            var menu = new WinForms.ContextMenuStrip();
            menu.Items.Add("打开消息中心", null, (s, e) => OpenInbox());
            menu.Items.Add("显示主窗口", null, (s, e) => ShowFromTray());
            menu.Items.Add(new WinForms.ToolStripSeparator());
            menu.Items.Add("退出", null, (s, e) => ExitApp());
            _tray.ContextMenuStrip = menu;
            _tray.DoubleClick += (s, e) => OpenInbox();
        }

        private void ShowFromTray()
        {
            Show();
            WindowState = WindowState.Normal;
            Activate();
        }

        public void ExitApp()
        {
            _reallyExit = true;
            if (_ws != null) { _ws.Dispose(); _ws = null; }
            if (_tray != null) { _tray.Visible = false; _tray.Dispose(); _tray = null; }
            NotifyManager.CloseAll();
            TtsService.Stop();
            Application.Current.Shutdown();
        }

        private void UpdateUnread()
        {
            TbUnread.Text = _unread > 0 ? _unread + " 条未读，点击「打开消息中心」查看" : "";
            UpdateTrayIcon(_unread);
            UpdateTrayTooltip();
        }

        private void UpdateTrayIcon(int unread)
        {
            var newIcon = BuildIcon(unread);
            if (_tray != null)
            {
                var old = _trayIcon;
                _trayIcon = newIcon;
                _tray.Icon = newIcon;
                if (old != null) old.Dispose();
            }
            else
            {
                newIcon.Dispose();
            }
        }

        private void UpdateTrayTooltip()
        {
            if (_tray == null) return;
            var status = TbStatus.Text;
            var tip = "叮咚 - " + _settings.TerminalCode;
            if (!string.IsNullOrEmpty(_settings.TerminalName)) tip += " " + _settings.TerminalName;
            tip += " (" + status + ")";
            if (tip.Length > 63) tip = tip.Substring(0, 63);  // 托盘提示上限 63 字符
            _tray.Text = tip;
        }

        /// <summary>运行时绘制托盘图标：蓝底"叮"，有未读时红底显示数量。</summary>
        private System.Drawing.Icon BuildIcon(int unread)
        {
            using (var bmp = new Bitmap(32, 32))
            using (var g = Graphics.FromImage(bmp))
            {
                g.SmoothingMode = SmoothingMode.AntiAlias;
                g.TextRenderingHint = System.Drawing.Text.TextRenderingHint.AntiAlias;
                var hasUnread = unread > 0;
                using (var brush = new SolidBrush(hasUnread
                    ? System.Drawing.Color.FromArgb(245, 108, 108)
                    : System.Drawing.Color.FromArgb(64, 158, 255)))
                {
                    g.FillEllipse(brush, 1, 1, 30, 30);
                }
                var text = hasUnread ? (unread > 99 ? "99" : unread.ToString()) : "叮";
                using (var font = new Font("Microsoft YaHei",
                    hasUnread ? (unread >= 10 ? 13f : 15f) : 14f,
                    System.Drawing.FontStyle.Bold))
                {
                    var size = g.MeasureString(text, font);
                    g.DrawString(text, font, System.Drawing.Brushes.White,
                        (32 - size.Width) / 2f, (32 - size.Height) / 2f);
                }
                IntPtr handle = bmp.GetHicon();
                try
                {
                    return (System.Drawing.Icon)System.Drawing.Icon.FromHandle(handle).Clone();
                }
                finally
                {
                    DestroyIcon(handle);
                }
            }
        }

        [DllImport("user32.dll", SetLastError = true)]
        private static extern bool DestroyIcon(IntPtr hIcon);
    }
}
