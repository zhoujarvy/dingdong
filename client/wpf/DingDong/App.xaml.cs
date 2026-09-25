using System;
using System.IO;
using System.Threading;
using System.Windows;
using DingDong.Services;

namespace DingDong
{
    public partial class App : Application
    {
        private Mutex _mutex;
        private Models.Settings _settings;

        protected override void OnStartup(StartupEventArgs e)
        {
            _mutex = new Mutex(true, "DingDong_SingleInstance", out bool createdNew);
            if (!createdNew)
            {
                MessageBox.Show("叮咚已在运行，请查看系统托盘（右下角）。", "叮咚",
                    MessageBoxButton.OK, MessageBoxImage.Information);
                Shutdown();
                return;
            }

            base.OnStartup(e);
            DispatcherUnhandledException += App_DispatcherUnhandledException;

            _settings = SettingsStore.Load();
            bool startMinimized = false;
            foreach (var arg in e.Args)
                if (string.Equals(arg, "--minimized", StringComparison.OrdinalIgnoreCase))
                    startMinimized = true;

            var win = new MainWindow(_settings, startMinimized);
            MainWindow = win;
        }

        private void App_DispatcherUnhandledException(object sender,
            System.Windows.Threading.DispatcherUnhandledExceptionEventArgs e)
        {
            try
            {
                var dir = Path.Combine(
                    Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData), "DingDong");
                Directory.CreateDirectory(dir);
                File.AppendAllText(Path.Combine(dir, "error.log"),
                    DateTime.Now + " " + e.Exception + Environment.NewLine);
            }
            catch { }
            MessageBox.Show("发生未处理的错误：" + e.Exception.Message, "叮咚",
                MessageBoxButton.OK, MessageBoxImage.Error);
            e.Handled = true;
        }

        protected override void OnExit(ExitEventArgs e)
        {
            if (_settings != null)
            {
                try { SettingsStore.Save(_settings); } catch { }
            }
            if (_mutex != null) _mutex.ReleaseMutex();
            base.OnExit(e);
        }
    }
}
