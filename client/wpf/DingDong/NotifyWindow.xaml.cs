using System;
using System.Diagnostics;
using System.Windows;
using System.Windows.Input;
using System.Windows.Media.Animation;
using DingDong.Models;

namespace DingDong
{
    /// <summary>右下角消息弹窗：点击打开全文页，到期自动关闭（悬停时暂停计时；0 秒 = 不自动关闭）。</summary>
    public partial class NotifyWindow : Window
    {
        /// <summary>用户点击弹窗打开全文页时触发（用于标记已读）。</summary>
        public event Action<Message> OpenRequested;

        private readonly Message _msg;
        private readonly string _fullUrl;
        private readonly int _autoCloseSec;
        private System.Windows.Threading.DispatcherTimer _timer;
        private bool _closing;

        public NotifyWindow(Message msg, string fullUrl, int autoCloseSec)
        {
            InitializeComponent();
            _msg = msg;
            _fullUrl = fullUrl;
            _autoCloseSec = autoCloseSec;

            TbTitle.Text = msg.Title;
            TbMeta.Text = (string.IsNullOrEmpty(msg.Sender) ? "" : msg.Sender + " · ") + msg.CreatedAt;
            TbContent.Text = msg.Preview;

            Opacity = 0;
            Loaded += (s, e) =>
            {
                var fade = new DoubleAnimation(0, 1, TimeSpan.FromMilliseconds(200));
                BeginAnimation(OpacityProperty, fade);
                StartAutoClose();
            };
        }

        private void StartAutoClose()
        {
            if (_autoCloseSec <= 0) return;   // 不自动关闭，等待人工点击
            _timer = new System.Windows.Threading.DispatcherTimer
            {
                Interval = TimeSpan.FromSeconds(_autoCloseSec)
            };
            _timer.Tick += (s, e) => CloseQuietly();
            _timer.Start();
        }

        private void Card_MouseEnter(object sender, MouseEventArgs e)
        {
            if (_timer != null) _timer.Stop();   // 悬停暂停自动关闭
        }

        private void Card_MouseLeave(object sender, MouseEventArgs e)
        {
            if (_timer != null) _timer.Start();
        }

        private void Card_MouseLeftButtonDown(object sender, MouseButtonEventArgs e)
        {
            OpenUrl();
        }

        private void OpenUrl()
        {
            try
            {
                Services.Browser.Open(_fullUrl);
                var handler = OpenRequested;
                if (handler != null) handler(_msg);
            }
            catch (Exception ex) { MessageBox.Show("打开网页失败：" + ex.Message, "叮咚"); }
            CloseQuietly();
        }

        private void BtnClose_Click(object sender, RoutedEventArgs e)
        {
            CloseQuietly();
        }

        /// <summary>静默关闭并带淡出动画；返回是否由用户主动点击打开。</summary>
        private void CloseQuietly()
        {
            if (_closing) return;
            _closing = true;
            if (_timer != null) _timer.Stop();

            var fade = new DoubleAnimation(1, 0, TimeSpan.FromMilliseconds(180));
            fade.Completed += (s, e) => { try { Close(); } catch { } };
            BeginAnimation(OpacityProperty, fade);
        }
    }
}
