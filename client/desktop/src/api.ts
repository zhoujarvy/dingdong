/** 服务端 HTTP API：注册 / 登录 / 注销 */

export interface TerminalIdentity {
  code: string;
  name: string;
  inbox_token: string;
}

async function post<T>(serverUrl: string, path: string, body: unknown): Promise<T> {
  const resp = await fetch(serverUrl.replace(/\/+$/, "") + path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    signal: AbortSignal.timeout(10_000),
  });
  const text = await resp.text();
  let data: unknown = null;
  try {
    data = JSON.parse(text);
  } catch {
    /* ignore */
  }
  if (!resp.ok) {
    const detail =
      data && typeof data === "object" && "detail" in data
        ? String((data as Record<string, unknown>).detail)
        : `HTTP ${resp.status}`;
    throw new Error(detail);
  }
  return data as T;
}

export const registerTerminal = (serverUrl: string, name: string) =>
  post<TerminalIdentity>(serverUrl, "/api/terminals/register", { name });

export const loginTerminal = (serverUrl: string, code: string, name: string) =>
  post<TerminalIdentity>(serverUrl, "/api/terminals/login", { code, name });

export const unregisterTerminal = (serverUrl: string, code: string, token: string) =>
  post<{ ok: boolean }>(serverUrl, "/api/terminals/unregister", { code, token });
