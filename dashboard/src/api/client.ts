import { env } from "../env";
import { getToken, onUnauthorized } from "../auth/token";

export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string,
  ) {
    super(message);
  }
}

/** JSON fetch against the ClearSky API with the signed-in user's token. */
export async function api<T>(path: string, init: { method?: string; body?: unknown; query?: Record<string, string | undefined> } = {}): Promise<T> {
  const params = new URLSearchParams();
  for (const [k, v] of Object.entries(init.query ?? {})) if (v) params.set(k, v);
  const qs = params.toString();
  const token = await getToken();
  const res = await fetch(`${env.apiUrl}${path}${qs ? `?${qs}` : ""}`, {
    method: init.method ?? "GET",
    headers: {
      ...(init.body !== undefined ? { "Content-Type": "application/json" } : {}),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: init.body !== undefined ? JSON.stringify(init.body) : undefined,
  });
  const text = await res.text();
  const data = text ? (JSON.parse(text) as unknown) : null;
  if (!res.ok) {
    const err = (data as { error?: { code?: string; message?: string } } | null)?.error;
    if (res.status === 401) onUnauthorized();
    throw new ApiError(res.status, err?.code ?? "error", err?.message ?? `Request failed (${res.status})`);
  }
  return data as T;
}
