using System;
using System.Diagnostics;
using System.Linq;
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

            if (_settings.Registered && !_settings.LoggedOut)
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
                FillServerBoxes(_settings.ServerUrl);
                if (_settings.LoggedOut && !string.IsNullOrEmpty(_settings.TerminalCode))
                {
                    // 退出登录后再启动：预填编码，直接进入登录模式
                    SetLoginMode(true);
                }
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

        // ================= 注册 / 登录 =================

        /// <summary>把 ServerUrl 拆成地址与端口填入输入框。</summary>
        private void FillServerBoxes(string serverUrl)
        {
            var host = (serverUrl ?? "").Trim().TrimEnd('/');
            if (host.StartsWith("http://", StringComparison.OrdinalIgnoreCase)) host = host.Substring(7);
            if (host.StartsWith("https://", StringComparison.OrdinalIgnoreCase)) host = host.Substring(8);
            var port = "";
            var idx = host.LastIndexOf(':');
            if (idx >= 0)
            {
                port = host.Substring(idx + 1);
                if (port.All(char.IsDigit) && port.Length > 0) host = host.Substring(0, idx);
                else port = "";
            }
            TxtServerHost.Text = string.IsNullOrEmpty(host) ? "127.0.0.1" : host;
            TxtServerPort.Text = string.IsNullOrEmpty(port) ? "80" : port;
        }

        /// <summary>由地址 + 端口输入框拼出服务器 URL。</summary>
        private string ServerUrlFromBoxes()
        {
            var host = TxtServerHost.Text.Trim().Trim().TrimEnd('/');
            var port = TxtServerPort.Text.Trim();
            return "http://" + host + (string.IsNullOrEmpty(port) || port == "80" ? "" : ":" + port);
        }

        private void SetLoginMode(bool login)
        {
            TbNameLabel.Visibility = login ? Visibility.Collapsed : Visibility.Visible;
            TxtTerminalName.Visibility = login ? Visibility.Collapsed : Visibility.Visible;
            TbCodeLabel.Visibility = login ? Visibility.Visible : Visibility.Collapsed;
            TxtLoginCode.Visibility = login ? Visibility.Visible : Visibility.Collapsed;
            TbLoginNameLabel.Visibility = login ? Visibility.Visible : Visibility.Collapsed;
            TxtLoginName.Visibility = login ? Visibility.Visible : Visibility.Collapsed;
            BtnRegister.Visibility = login ? Visibility.Collapsed : Visibility.Visible;
            BtnLogin.Visibility = login ? Visibility.Visible : Visibility.Collapsed;
            TbModeSwitch.Text = login ? "没有编码？点此注册新终端" : "已有终端编码？点此登录";
            TbRegisterTip.Text = login ? "输入终端编码与名称登录，需与注册时一致" : "注册后将获得一个 6 位终端编码，请妥善保存";
        }

        private void TbModeSwitch_Click(object sender, System.Windows.Input.MouseButtonEventArgs e)
        {
            SetLoginMode(BtnLogin.Visibility != Visibility.Visible);
        }

        private async void BtnRegister_Click(object sender, RoutedEventArgs e) => await RegisterAsync();

        private async void TxtTerminalName_KeyDown(object sender, System.Windows.Input.KeyEventArgs e)
        {
            if (e.Key == System.Windows.Input.Key.Enter) await RegisterAsync();
        }

        private async void BtnLogin_Click(object sender, RoutedEventArgs e) => await LoginAsync();

        private async void TxtLoginCode_KeyDown(object sender, System.Windows.Input.KeyEventArgs e)
        {
            if (e.Key == System.Windows.Input.Key.Enter) await LoginAsync();
        }

        private async System.Threading.Tasks.Task RegisterAsync()
        {
            var server = ServerUrlFromBoxes();
            var name = TxtTerminalName.Text.Trim();
            if (string.IsNullOrEmpty(TxtServerHost.Text.Trim())) { TbRegisterTip.Text = "请输入服务器地址"; return; }
            if (name.Length == 0) { TbRegisterTip.Text = "请输入终端名称"; return; }

            BtnRegister.IsEnabled = false;
            TbRegisterTip.Text = "正在注册…";
            try
            {
                var result = await System.Threading.Tasks.Task.Run(
                    () => ApiClient.Register(server, name));
                ApplyIdentity(server, result);
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

        private async System.Threading.Tasks.Task LoginAsync()
        {
            var server = ServerUrlFromBoxes();
            var code = TxtLoginCode.Text.Trim().ToUpper();
            var name = TxtLoginName.Text.Trim();
            if (string.IsNullOrEmpty(TxtServerHost.Text.Trim())) { TbRegisterTip.Text = "请输入服务器地址"; return; }
            if (code.Length != 6) { TbRegisterTip.Text = "请输入 6 位终端编码"; return; }
            if (name.Length == 0) { TbRegisterTip.Text = "请输入终端名称（注册时填写）"; return; }

            BtnLogin.IsEnabled = false;
            TbRegisterTip.Text = "正在登录…";
            try
            {
                var result = await System.Threading.Tasks.Task.Run(
                    () => ApiClient.Login(server, code, name));
                ApplyIdentity(server, result);
                _unread = 0;
                ShowMainPanel();
                StartWs();
            }
            catch (Exception ex)
            {
                TbRegisterTip.Text = "登录失败：" + ex.Message;
            }
            finally
            {
                BtnLogin.IsEnabled = true;
            }
        }

        /// <summary>注册/登录成功后，落地终端身份信息。</summary>
        private void ApplyIdentity(string server, System.Collections.Generic.Dictionary<string, object> result)
        {
            _settings.ServerUrl = server;
            _settings.TerminalCode = Convert.ToString(result["code"]);
            _settings.TerminalName = Convert.ToString(result["name"]);
            _settings.InboxToken = Convert.ToString(result["inbox_token"]);
            _settings.LoggedOut = false;
            SettingsStore.Save(_settings);
        }

        private void ShowMainPanel()
        {
            RegisterPanel.Visibility = Visibility.Collapsed;
            MainPanel.Visibility = Visibility.Visible;
            TbCode.Text = _settings.TerminalCode;
            TbTerminalName.Text = _settings.TerminalName;
            UpdateUnread();

            // 载入设置
            {
                var host = (_settings.ServerUrl ?? "").Trim().TrimEnd('/');
                if (host.StartsWith("http://", StringComparison.OrdinalIgnoreCase)) host = host.Substring(7);
                var port = "80";
                var idx = host.LastIndexOf(':');
                if (idx >= 0)
                {
                    var p = host.Substring(idx + 1);
                    if (p.Length > 0 && p.All(char.IsDigit)) { port = p; host = host.Substring(0, idx); }
                }
                TxtSettingsHost.Text = host;
                TxtSettingsPort.Text = port;
            }
            ChkSound.IsChecked = _settings.SoundEnabled;
            ChkTts.IsChecked = _settings.TtsEnabled;
            CmbTtsMode.SelectedIndex = _settings.TtsMode == "both" ? 1 : 0;
            ChkAutoStart.IsChecked = _settings.AutoStart;
            SelectNotifyClose(_settings.NotifyAutoCloseSec);
        }

        /// <summary>按秒数选中弹窗关闭选项（项顺序：10,30,60,180,0=不关闭）；非预置值取最接近档位。</summary>
        private void SelectNotifyClose(int sec)
        {
            int[] order = { 10, 30, 60, 180, 0 };
            int idx = Array.IndexOf(order, sec);
            if (idx < 0)
            {
                if (sec <= 0) idx = 4;
                else if (sec < 20) idx = 0;
                else if (sec < 45) idx = 1;
                else if (sec < 120) idx = 2;
                else idx = 3;
            }
            CmbNotifyClose.SelectedIndex = idx;
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
            TbStatus.Foreground = color;
            var scb = color as System.Windows.Media.SolidColorBrush;
            StatusPill.Background = new System.Windows.Media.SolidColorBrush
            {
                Color = scb != null ? scb.Color : System.Windows.Media.Colors.Gray,
                Opacity = 0.12,
            };
            Title = "叮咚 - " + (_settings.Registered && !_settings.LoggedOut ? text : "未登录");
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
            BackToRegisterPanel(false);
        }

        /// <summary>回到注册/登录面板。keepCode=true 时保留编码并切到登录模式（退出登录）；false 时清空身份（注销/被注销）。</summary>
        private void BackToRegisterPanel(bool keepCode)
        {
            if (keepCode)
            {
                _settings.LoggedOut = true;
                SettingsStore.Save(_settings);
            }
            else
            {
                SettingsStore.Reset(_settings);
                TxtTerminalName.Clear();
            }
            _unread = 0;
            UpdateUnread();
            if (_ws != null) { _ws.Dispose(); _ws = null; }
            FillServerBoxes(_settings.ServerUrl);
            SetLoginMode(keepCode);
            if (keepCode)
            {
                TxtLoginCode.Text = _settings.TerminalCode;
                TxtLoginName.Text = _settings.TerminalName;
            }
            TbRegisterTip.Text = keepCode
                ? "已退出登录，编码与名称已保留，可在此或新电脑上登录"
                : "注册后将获得一个 6 位终端编码，请妥善保存";
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
            _settings.NotifyAutoCloseSec = Convert.ToInt32((CmbNotifyClose.SelectedItem as ComboBoxItem)?.Tag as string ?? "60");
            var autoStart = ChkAutoStart.IsChecked == true;
            _settings.AutoStart = autoStart;
            SetAutoStart(autoStart);

            var newHost = TxtSettingsHost.Text.Trim().TrimEnd('/');
            var newPort = TxtSettingsPort.Text.Trim();
            if (newPort.Length == 0 || !newPort.All(char.IsDigit))
            {
                MessageBox.Show(this, "端口必须是数字", "叮咚", MessageBoxButton.OK, MessageBoxImage.Warning);
                return;
            }
            var newServer = "http://" + newHost + (newPort == "80" ? "" : ":" + newPort);
            var serverChanged = newServer != _settings.ServerUrl && newHost.Length > 0;
            if (serverChanged) _settings.ServerUrl = newServer;
            SettingsStore.Save(_settings);

            if (serverChanged && _ws != null)
            {
                _ws.ServerUrl = _settings.ServerUrl;
                _ws.Restart();
            }
            MessageBox.Show(this, "设置已保存", "叮咚", MessageBoxButton.OK, MessageBoxImage.Information);
        }

        /// <summary>退出登录：仅断开本机连接，编码/名称保留，可在本机或新电脑凭编码重新登录。</summary>
        private void BtnLogout_Click(object sender, RoutedEventArgs e)
        {
            if (MessageBox.Show(this,
                    "确定退出登录？终端编码与名称将保留，可在此电脑或新电脑上凭编码重新登录。",
                    "叮咚", MessageBoxButton.OKCancel, MessageBoxImage.Question) != MessageBoxResult.OK)
                return;
            BackToRegisterPanel(true);
        }

        private async void BtnUnregister_Click(object sender, RoutedEventArgs e)
        {
            if (MessageBox.Show(this,
                    "确定注销此终端？注销后编号作废、不再接收消息，且无法再登录，只能重新注册。",
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
            BackToRegisterPanel(false);
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
        private System.Drawing.Icon _bellIcon;

        /// <summary>共享铃铛图标（Assets/app.ico，与网页 favicon 同款），无未读时作为托盘图标。</summary>
        private System.Drawing.Icon BellIcon()
        {
            if (_bellIcon == null)
            {
                var sri = Application.GetResourceStream(
                    new Uri("pack://application:,,,/Assets/app.ico"));
                _bellIcon = new System.Drawing.Icon(sri.Stream, 32, 32);
            }
            return _bellIcon;
        }

        private void InitTray()
        {
            _tray = new WinForms.NotifyIcon
            {
                Visible = true,
                Text = "叮咚",
            };
            _trayIcon = BellIcon();
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
            if (_bellIcon != null) { _bellIcon.Dispose(); _bellIcon = null; }
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
            var newIcon = unread > 0 ? BuildIcon(unread) : BellIcon();
            if (_tray != null)
            {
                var old = _trayIcon;
                _trayIcon = newIcon;
                _tray.Icon = newIcon;
                // 共享铃铛图标不参与释放
                if (old != null && old != _bellIcon) old.Dispose();
            }
            else if (newIcon != _bellIcon)
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
