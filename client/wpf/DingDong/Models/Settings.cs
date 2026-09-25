namespace DingDong.Models
{
    /// <summary>客户端设置，持久化到 %AppData%\DingDong\settings.json。</summary>
    public class Settings
    {
        public string ServerUrl { get; set; } = "";
        public string TerminalCode { get; set; } = "";
        public string TerminalName { get; set; } = "";
        /// <summary>网页消息中心访问令牌（服务器下发，用于拼接消息中心地址）。</summary>
        public string InboxToken { get; set; } = "";
        public bool SoundEnabled { get; set; } = true;
        public bool TtsEnabled { get; set; } = false;
        /// <summary>"title"=仅朗读标题；"both"=朗读标题+内容摘要</summary>
        public string TtsMode { get; set; } = "title";
        public bool AutoStart { get; set; } = false;
        /// <summary>已退出登录（本地保留编码，换机后可凭编码重新登录）。</summary>
        public bool LoggedOut { get; set; } = false;

        [System.Xml.Serialization.XmlIgnore]
        public bool Registered
        {
            get { return !string.IsNullOrEmpty(ServerUrl) && !string.IsNullOrEmpty(TerminalCode); }
        }
    }
}
