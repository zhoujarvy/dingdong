using System;
using System.Collections.Generic;
using System.IO;
using DingDong.Models;

namespace DingDong.Services
{
    /// <summary>设置的加载与保存（JSON，%AppData%\DingDong\settings.json）。</summary>
    public static class SettingsStore
    {
        private static readonly string Dir =
            Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData), "DingDong");
        private static readonly string FilePath = Path.Combine(Dir, "settings.json");

        public static Settings Load()
        {
            try
            {
                if (File.Exists(FilePath))
                {
                    var dict = Json.ParseObject(File.ReadAllText(FilePath));
                    if (dict != null)
                    {
                        return new Settings
                        {
                            ServerUrl = Json.GetStr(dict, "ServerUrl"),
                            TerminalCode = Json.GetStr(dict, "TerminalCode"),
                            TerminalName = Json.GetStr(dict, "TerminalName"),
                            InboxToken = Json.GetStr(dict, "InboxToken"),
                            SoundEnabled = Json.GetBool(dict, "SoundEnabled", true),
                            TtsEnabled = Json.GetBool(dict, "TtsEnabled", false),
                            TtsMode = Json.GetStr(dict, "TtsMode", "title"),
                            AutoStart = Json.GetBool(dict, "AutoStart", false),
                        };
                    }
                }
            }
            catch { /* 损坏则重建 */ }
            return new Settings();
        }

        public static void Save(Settings s)
        {
            Directory.CreateDirectory(Dir);
            File.WriteAllText(FilePath, Json.Serialize(new Dictionary<string, object>
            {
                { "ServerUrl", s.ServerUrl ?? "" },
                { "TerminalCode", s.TerminalCode ?? "" },
                { "TerminalName", s.TerminalName ?? "" },
                { "InboxToken", s.InboxToken ?? "" },
                { "SoundEnabled", s.SoundEnabled },
                { "TtsEnabled", s.TtsEnabled },
                { "TtsMode", s.TtsMode ?? "title" },
                { "AutoStart", s.AutoStart },
            }));
        }

        /// <summary>清空注册信息（注销终端），保留服务器地址便于重新注册。</summary>
        public static void Reset(Settings settings)
        {
            settings.TerminalCode = "";
            settings.TerminalName = "";
            settings.InboxToken = "";
            Save(settings);
        }
    }
}
