import { createContext, type PropsWithChildren, useCallback, useContext, useMemo } from "react";
import type { TokenPair } from "./models";

export const API_BASE = "/api";
export const TOKEN_KEY = "yukinoise.auth.tokens";

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

export function readTokens(): TokenPair | null {
  try {
    return JSON.parse(localStorage.getItem(TOKEN_KEY) ?? "null") as TokenPair | null;
  } catch {
    return null;
  }
}

export async function responseError(response: Response): Promise<string> {
  const payload = await response.json().catch(() => null) as { detail?: string | Array<{ msg?: string }> } | null;
  if (typeof payload?.detail === "string") return payload.detail;
  if (Array.isArray(payload?.detail)) return payload.detail.map((item) => item.msg).filter(Boolean).join(" · ");
  return `Сервер ответил с кодом ${response.status}`;
}

interface ApiContextValue {
  tokens: TokenPair | null;
  request<T>(path: string, init?: RequestInit): Promise<T>;
  upload<T>(path: string, form: FormData, method?: string): Promise<T>;
}

const ApiContext = createContext<ApiContextValue | null>(null);

export function ApiProvider({
  tokens,
  onTokens,
  onUnauthorized,
  children,
}: PropsWithChildren<{
  tokens: TokenPair | null;
  onTokens(tokens: TokenPair): void;
  onUnauthorized(): void;
}>) {
  const execute = useCallback(async <T,>(path: string, init: RequestInit = {}, retry = true): Promise<T> => {
    const headers = new Headers(init.headers);
    if (tokens?.access_token) headers.set("Authorization", `Bearer ${tokens.access_token}`);
    if (init.body && !(init.body instanceof FormData) && !headers.has("Content-Type")) headers.set("Content-Type", "application/json");
    let response = await fetch(`${API_BASE}${path}`, { ...init, headers });

    if (response.status === 401 && retry && tokens?.refresh_token) {
      const refreshed = await fetch(`${API_BASE}/auth/refresh`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: tokens.refresh_token }),
      });
      if (refreshed.ok) {
        const next = await refreshed.json() as TokenPair;
        onTokens(next);
        headers.set("Authorization", `Bearer ${next.access_token}`);
        response = await fetch(`${API_BASE}${path}`, { ...init, headers });
      } else {
        onUnauthorized();
      }
    }

    if (!response.ok) throw new ApiError(await responseError(response), response.status);
    if (response.status === 204) return undefined as T;
    return response.json() as Promise<T>;
  }, [onTokens, onUnauthorized, tokens]);

  const value = useMemo<ApiContextValue>(() => ({
    tokens,
    request: execute,
    upload: (path, form, method = "POST") => execute(path, { method, body: form }),
  }), [execute, tokens]);

  return <ApiContext.Provider value={value}>{children}</ApiContext.Provider>;
}

export function useApi(): ApiContextValue {
  const value = useContext(ApiContext);
  if (!value) throw new Error("useApi must be used inside ApiProvider");
  return value;
}
