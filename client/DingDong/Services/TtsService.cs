using System.Speech.Synthesis;
using DingDong.Models;

namespace DingDong.Services
{
    /// <summary>使用 Windows 系统语音（SAPI）朗读消息简介。</summary>
    public static class TtsService
    {
        private static SpeechSynthesizer _synth;

        private static SpeechSynthesizer Synth
        {
            get
            {
                if (_synth == null)
                {
                    _synth = new SpeechSynthesizer();
                    _synth.Rate = 1;
                    // 优先选择中文语音
                    foreach (var voice in _synth.GetInstalledVoices())
                    {
                        if (!voice.Enabled) continue;
                        var info = voice.VoiceInfo;
                        if (info.Culture != null && info.Culture.Name.StartsWith("zh"))
                        {
                            try { _synth.SelectVoice(info.Name); } catch { }
                            break;
                        }
                    }
                }
                return _synth;
            }
        }

        public static void SpeakMessage(Message msg, string mode)
        {
            var text = msg.Title ?? "";
            if (mode == "both")
            {
                var brief = msg.Content ?? "";
                if (brief.Length > 60) brief = brief.Substring(0, 60);
                if (brief.Length > 0) text = text + "。" + brief;
            }
            if (string.IsNullOrEmpty(text)) return;
            Speak(text);
        }

        public static void Speak(string text)
        {
            try
            {
                var synth = Synth;
                synth.SpeakAsyncCancelAll();  // 新消息打断上一条，避免排队堆积
                synth.SpeakAsync(text);
            }
            catch { /* 语音引擎异常不影响主流程 */ }
        }

        public static void Stop()
        {
            try { if (_synth != null) _synth.SpeakAsyncCancelAll(); } catch { }
        }
    }
}
