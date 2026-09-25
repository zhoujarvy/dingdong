using System.ComponentModel;
using System.Runtime.CompilerServices;

namespace DingDong.Models
{
    /// <summary>一条推送消息（服务端为唯一数据源，客户端仅持有展示副本）。</summary>
    public class Message : INotifyPropertyChanged
    {
        public int Id { get; set; }
        public string Title { get; set; }
        public string Content { get; set; }
        public string Sender { get; set; }
        /// <summary>相对于服务器的全文页路径，如 /m/12?token=xx</summary>
        public string Url { get; set; }
        public string CreatedAt { get; set; }
        public string PushedAt { get; set; }

        private bool _read;
        public bool Read
        {
            get { return _read; }
            set
            {
                if (_read != value)
                {
                    _read = value;
                    OnPropertyChanged();
                }
            }
        }

        public string Preview
        {
            get
            {
                var c = Content ?? "";
                return string.IsNullOrEmpty(c) ? "（无内容）" : c;
            }
        }

        public event PropertyChangedEventHandler PropertyChanged;

        private void OnPropertyChanged([CallerMemberName] string name = null)
        {
            var handler = PropertyChanged;
            if (handler != null) handler(this, new PropertyChangedEventArgs(name));
        }
    }
}
