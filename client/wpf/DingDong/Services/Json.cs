using System;
using System.Collections;
using System.Collections.Generic;
using System.Globalization;
using System.Text;

namespace DingDong.Services
{
    /// <summary>
    /// 极简 JSON 序列化/反序列化工具（避免引入 System.Web.Extensions/System.Web 依赖）。
    /// 支持：字符串、布尔、数值、null、字典、列表。
    /// </summary>
    public static class Json
    {
        // ================= 序列化 =================
        public static string Serialize(object value)
        {
            var sb = new StringBuilder();
            WriteValue(sb, value);
            return sb.ToString();
        }

        private static void WriteValue(StringBuilder sb, object value)
        {
            if (value == null) { sb.Append("null"); return; }
            if (value is string) { WriteString(sb, (string)value); return; }
            if (value is bool) { sb.Append((bool)value ? "true" : "false"); return; }
            if (value is char) { WriteString(sb, value.ToString()); return; }
            if (value is float || value is double || value is decimal)
            {
                sb.Append(Convert.ToString(value, CultureInfo.InvariantCulture));
                return;
            }
            if (value is byte || value is sbyte || value is short || value is ushort ||
                value is int || value is uint || value is long || value is ulong)
            {
                sb.Append(Convert.ToString(value, CultureInfo.InvariantCulture));
                return;
            }
            if (value is IDictionary dict)
            {
                sb.Append('{');
                bool first = true;
                foreach (DictionaryEntry entry in dict)
                {
                    if (!first) sb.Append(',');
                    first = false;
                    WriteString(sb, Convert.ToString(entry.Key, CultureInfo.InvariantCulture));
                    sb.Append(':');
                    WriteValue(sb, entry.Value);
                }
                sb.Append('}');
                return;
            }
            if (value is IEnumerable list)
            {
                sb.Append('[');
                bool first = true;
                foreach (var item in list)
                {
                    if (!first) sb.Append(',');
                    first = false;
                    WriteValue(sb, item);
                }
                sb.Append(']');
                return;
            }
            WriteString(sb, value.ToString());
        }

        private static void WriteString(StringBuilder sb, string s)
        {
            sb.Append('"');
            if (s != null)
            {
                foreach (char c in s)
                {
                    switch (c)
                    {
                        case '"': sb.Append("\\\""); break;
                        case '\\': sb.Append("\\\\"); break;
                        case '\b': sb.Append("\\b"); break;
                        case '\f': sb.Append("\\f"); break;
                        case '\n': sb.Append("\\n"); break;
                        case '\r': sb.Append("\\r"); break;
                        case '\t': sb.Append("\\t"); break;
                        default:
                            if (c < ' ')
                                sb.Append("\\u").Append(((int)c).ToString("x4"));
                            else
                                sb.Append(c);
                            break;
                    }
                }
            }
            sb.Append('"');
        }

        // ================= 反序列化 =================
        public static object Parse(string json)
        {
            int pos = 0;
            object result = ParseValue(json, ref pos);
            SkipSpace(json, ref pos);
            if (pos != json.Length) throw new FormatException("JSON 末尾存在多余字符");
            return result;
        }

        public static Dictionary<string, object> ParseObject(string json)
        {
            return Parse(json) as Dictionary<string, object>;
        }

        private static object ParseValue(string s, ref int pos)
        {
            SkipSpace(s, ref pos);
            if (pos >= s.Length) throw new FormatException("JSON 意外结束");
            char c = s[pos];
            if (c == '{') return ParseObj(s, ref pos);
            if (c == '[') return ParseArr(s, ref pos);
            if (c == '"') return ParseStr(s, ref pos);
            if (c == 't') { Expect(s, ref pos, "true"); return true; }
            if (c == 'f') { Expect(s, ref pos, "false"); return false; }
            if (c == 'n') { Expect(s, ref pos, "null"); return null; }
            return ParseNum(s, ref pos);
        }

        private static Dictionary<string, object> ParseObj(string s, ref int pos)
        {
            var dict = new Dictionary<string, object>();
            pos++;  // 跳过 '{'
            SkipSpace(s, ref pos);
            if (pos < s.Length && s[pos] == '}') { pos++; return dict; }
            while (true)
            {
                SkipSpace(s, ref pos);
                if (pos >= s.Length || s[pos] != '"')
                    throw new FormatException("JSON 对象键必须是字符串");
                string key = ParseStr(s, ref pos);
                SkipSpace(s, ref pos);
                if (pos >= s.Length || s[pos] != ':')
                    throw new FormatException("JSON 对象缺少 ':'");
                pos++;
                dict[key] = ParseValue(s, ref pos);
                SkipSpace(s, ref pos);
                if (pos >= s.Length) throw new FormatException("JSON 对象意外结束");
                if (s[pos] == ',') { pos++; continue; }
                if (s[pos] == '}') { pos++; return dict; }
                throw new FormatException("JSON 对象缺少 ',' 或 '}'");
            }
        }

        private static List<object> ParseArr(string s, ref int pos)
        {
            var list = new List<object>();
            pos++;  // 跳过 '['
            SkipSpace(s, ref pos);
            if (pos < s.Length && s[pos] == ']') { pos++; return list; }
            while (true)
            {
                list.Add(ParseValue(s, ref pos));
                SkipSpace(s, ref pos);
                if (pos >= s.Length) throw new FormatException("JSON 数组意外结束");
                if (s[pos] == ',') { pos++; continue; }
                if (s[pos] == ']') { pos++; return list; }
                throw new FormatException("JSON 数组缺少 ',' 或 ']'");
            }
        }

        private static string ParseStr(string s, ref int pos)
        {
            pos++;  // 跳过开头 '"'
            var sb = new StringBuilder();
            while (pos < s.Length)
            {
                char c = s[pos++];
                if (c == '"') return sb.ToString();
                if (c == '\\')
                {
                    if (pos >= s.Length) break;
                    char e = s[pos++];
                    switch (e)
                    {
                        case '"': sb.Append('"'); break;
                        case '\\': sb.Append('\\'); break;
                        case '/': sb.Append('/'); break;
                        case 'b': sb.Append('\b'); break;
                        case 'f': sb.Append('\f'); break;
                        case 'n': sb.Append('\n'); break;
                        case 'r': sb.Append('\r'); break;
                        case 't': sb.Append('\t'); break;
                        case 'u':
                            if (pos + 4 > s.Length) throw new FormatException("\\u 转义不完整");
                            sb.Append((char)Convert.ToInt32(s.Substring(pos, 4), 16));
                            pos += 4;
                            break;
                        default: throw new FormatException("无效的转义字符 \\" + e);
                    }
                }
                else
                {
                    sb.Append(c);
                }
            }
            throw new FormatException("JSON 字符串未闭合");
        }

        private static object ParseNum(string s, ref int pos)
        {
            int start = pos;
            while (pos < s.Length && "+-.eE0123456789".IndexOf(s[pos]) >= 0) pos++;
            string num = s.Substring(start, pos - start);
            long l;
            if (long.TryParse(num, NumberStyles.Integer, CultureInfo.InvariantCulture, out l))
                return l;
            double d;
            if (double.TryParse(num, NumberStyles.Float, CultureInfo.InvariantCulture, out d))
                return d;
            throw new FormatException("无法解析数值: " + num);
        }

        private static void Expect(string s, ref int pos, string word)
        {
            if (pos + word.Length > s.Length || s.Substring(pos, word.Length) != word)
                throw new FormatException("JSON 字面量不匹配");
            pos += word.Length;
        }

        private static void SkipSpace(string s, ref int pos)
        {
            while (pos < s.Length && char.IsWhiteSpace(s[pos])) pos++;
        }

        // ================= 取值助手 =================
        public static string GetStr(Dictionary<string, object> dict, string key, string def = "")
        {
            object v;
            if (dict != null && dict.TryGetValue(key, out v) && v != null)
                return Convert.ToString(v);
            return def;
        }

        public static bool GetBool(Dictionary<string, object> dict, string key, bool def = false)
        {
            object v;
            if (dict != null && dict.TryGetValue(key, out v) && v is bool)
                return (bool)v;
            return def;
        }

        public static int GetInt(Dictionary<string, object> dict, string key, int def = 0)
        {
            object v;
            if (dict != null && dict.TryGetValue(key, out v) && v != null)
            {
                try { return Convert.ToInt32(v); }
                catch { return def; }
            }
            return def;
        }
    }
}
