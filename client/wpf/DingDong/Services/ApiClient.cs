using System;
using System.Collections.Generic;
using System.Net.Http;
using System.Text;

namespace DingDong.Services
{
    /// <summary>HTTP 接口（目前仅终端注册）。</summary>
    public static class ApiClient
    {
        /// <summary>向服务器注册终端，返回包含 code/name 的字典；失败抛异常。</summary>
        public static Dictionary<string, object> Register(string serverUrl, string name)
        {
            using (var http = new HttpClient())
            {
                http.Timeout = TimeSpan.FromSeconds(10);
                var url = serverUrl.TrimEnd('/') + "/api/terminals/register";
                var body = Json.Serialize(new Dictionary<string, object> { { "name", name } });
                var resp = http.PostAsync(url,
                    new StringContent(body, Encoding.UTF8, "application/json")).GetAwaiter().GetResult();
                var text = resp.Content.ReadAsStringAsync().GetAwaiter().GetResult();
                if (!resp.IsSuccessStatusCode)
                {
                    string detail = "";
                    try
                    {
                        var err = Json.ParseObject(text);
                        if (err != null) detail = Json.GetStr(err, "detail");
                    }
                    catch { }
                    throw new Exception(string.IsNullOrEmpty(detail)
                        ? "注册失败（HTTP " + (int)resp.StatusCode + "）" : detail);
                }
                var data = Json.ParseObject(text);
                if (data == null || !data.ContainsKey("code"))
                    throw new Exception("服务器返回数据异常");
                return data;
            }
        }

        /// <summary>登录已有终端（编码 + 名称双重验证，换机重登场景），返回 code/name/inbox_token；失败抛异常。</summary>
        public static Dictionary<string, object> Login(string serverUrl, string code, string name)
        {
            using (var http = new HttpClient())
            {
                http.Timeout = TimeSpan.FromSeconds(10);
                var url = serverUrl.TrimEnd('/') + "/api/terminals/login";
                var body = Json.Serialize(new Dictionary<string, object>
                {
                    { "code", code.Trim().ToUpper() },
                    { "name", name.Trim() },
                });
                var resp = http.PostAsync(url,
                    new StringContent(body, Encoding.UTF8, "application/json")).GetAwaiter().GetResult();
                var text = resp.Content.ReadAsStringAsync().GetAwaiter().GetResult();
                if (!resp.IsSuccessStatusCode)
                {
                    string detail = "";
                    try
                    {
                        var err = Json.ParseObject(text);
                        if (err != null) detail = Json.GetStr(err, "detail");
                    }
                    catch { }
                    throw new Exception(string.IsNullOrEmpty(detail)
                        ? "登录失败（HTTP " + (int)resp.StatusCode + "）" : detail);
                }
                var data = Json.ParseObject(text);
                if (data == null || !data.ContainsKey("code"))
                    throw new Exception("服务器返回数据异常");
                return data;
            }
        }

        /// <summary>向服务器申请注销终端（凭终端编码 + 消息中心令牌）。失败抛异常。</summary>
        public static void Unregister(string serverUrl, string code, string inboxToken)
        {
            using (var http = new HttpClient())
            {
                http.Timeout = TimeSpan.FromSeconds(10);
                var url = serverUrl.TrimEnd('/') + "/api/terminals/unregister";
                var body = Json.Serialize(new Dictionary<string, object>
                {
                    { "code", code },
                    { "token", inboxToken },
                });
                var resp = http.PostAsync(url,
                    new StringContent(body, Encoding.UTF8, "application/json")).GetAwaiter().GetResult();
                if (!resp.IsSuccessStatusCode)
                {
                    var text = resp.Content.ReadAsStringAsync().GetAwaiter().GetResult();
                    string detail = "";
                    try
                    {
                        var err = Json.ParseObject(text);
                        if (err != null) detail = Json.GetStr(err, "detail");
                    }
                    catch { }
                    throw new Exception(string.IsNullOrEmpty(detail)
                        ? "注销失败（HTTP " + (int)resp.StatusCode + "）" : detail);
                }
            }
        }
    }
}
