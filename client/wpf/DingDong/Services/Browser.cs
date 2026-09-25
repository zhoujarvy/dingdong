using System;
using System.Diagnostics;
using System.IO;

namespace DingDong.Services
{
    /// <summary>打开网页：优先使用谷歌浏览器，未安装时回退系统默认浏览器。</summary>
    public static class Browser
    {
        private static readonly string[] ChromePaths =
        {
            Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.ProgramFiles),
                @"Google\Chrome\Application\chrome.exe"),
            Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.ProgramFilesX86),
                @"Google\Chrome\Application\chrome.exe"),
            Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
                @"Google\Chrome\Application\chrome.exe"),
        };

        public static void Open(string url)
        {
            foreach (var path in ChromePaths)
            {
                if (File.Exists(path))
                {
                    Process.Start(path, "\"" + url + "\"");
                    return;
                }
            }
            // 回退：默认浏览器
            Process.Start(new ProcessStartInfo
            {
                FileName = url,
                UseShellExecute = true,
            });
        }
    }
}
