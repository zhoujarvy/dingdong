using System;
using System.Collections.Generic;
using System.IO;
using System.Media;
using System.Reflection;
using System.Windows;
using DingDong.Models;

namespace DingDong.Services
{
    /// <summary>消息到达后的表现：提示音、TTS 朗读、右下角弹窗堆叠管理。</summary>
    public class NotifyManager
    {
        private const int MaxVisiblePopups = 4;

        private static readonly List<NotifyWindow> _popups = new List<NotifyWindow>();
        private static SoundPlayer _player;
        private static Window _owner;

        /// <summary>弹窗被点击时回调（sender=null），由外部接通 MarkRead。</summary>
        public static Action<Message> PopupOpened;

        public static void Init(Window owner)
        {
            _owner = owner;
            try
            {
                var stream = Assembly.GetExecutingAssembly()
                    .GetManifestResourceStream("DingDong.Assets.ding.wav");
                if (stream != null) _player = new SoundPlayer(stream);
            }
            catch { }
        }

        /// <summary>完整的通知流程：声音 + 语音 + 弹窗。</summary>
        public static void Notify(Message msg, Settings settings)
        {
            if (settings.SoundEnabled) PlaySound();
            if (settings.TtsEnabled) TtsService.SpeakMessage(msg, settings.TtsMode);
            ShowPopup(msg, settings.ServerUrl, settings.NotifyAutoCloseSec);
        }

        public static void PlaySound()
        {
            try
            {
                if (_player != null) _player.Play();
                else SystemSounds.Asterisk.Play();   // 兜底：系统提示音
            }
            catch { }
        }

        private static void ShowPopup(Message msg, string serverUrl, int autoCloseSec)
        {
            var url = BuildUrl(serverUrl, msg.Url);
            var win = new NotifyWindow(msg, url, autoCloseSec);
            win.OpenRequested += m =>
            {
                var handler = PopupOpened;
                if (handler != null) handler(m);
            };
            win.Closed += (s, e) => { _popups.Remove(win); RepositionAll(); };
            win.Show();
            _popups.Add(win);
            RepositionAll();
        }

        private static void RepositionAll()
        {
            // 屏幕右下角向上堆叠，最多同时显示 MaxVisiblePopups 个，多余的立即关闭最旧的
            while (_popups.Count > MaxVisiblePopups)
                _popups[0].Close();

            double bottom = SystemParameters.WorkArea.Bottom;
            double right = SystemParameters.WorkArea.Right;
            double gap = 4;
            foreach (var win in _popups)
            {
                win.UpdateLayout();  // 确保 SizeToContent 生效
                double h = win.ActualHeight > 0 ? win.ActualHeight : 100;
                win.Left = right - win.Width - 6;
                win.Top = bottom - h - gap;
                bottom = bottom - h - gap;
            }
        }

        public static void CloseAll()
        {
            foreach (var win in _popups.ToArray())
                try { win.Close(); } catch { }
            _popups.Clear();
        }

        private static string BuildUrl(string serverUrl, string path)
        {
            if (string.IsNullOrEmpty(path)) return serverUrl;
            return serverUrl.TrimEnd('/') + (path.StartsWith("/") ? path : "/" + path);
        }
    }
}
