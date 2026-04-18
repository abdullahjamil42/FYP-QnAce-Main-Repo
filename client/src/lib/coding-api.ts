import { getSupabaseClient } from "@/lib/supabase";

export function getApiBase(): string {
  return (
    process.env.NEXT_PUBLIC_QACE_API_URL?.replace(/\/$/, "") ||
    "http://127.0.0.1:8000"
  );
}

async function authHeaders(): Promise<Record<string, string>> {
  const h: Record<string, string> = { "Content-Type": "application/json" };
  const client = getSupabaseClient();
  if (client) {
    const { data } = await client.auth.getSession();
    const token = data.session?.access_token;
    if (token) {
      h.Authorization = `Bearer ${token}`;
    }
  }
  return h;
}

export async function apiGet<T>(path: string): Promise<T> {
  const base = getApiBase();
  const headers = await authHeaders();
  const r = await fetch(`${base}${path}`, { headers });
  if (!r.ok) {
    const t = await r.text();
    throw new Error(`${r.status}: ${t.slice(0, 400)}`);
  }
  return r.json() as Promise<T>;
}

export async function apiPost<T>(path: string, body: unknown): Promise<T> {
  const base = getApiBase();
  const headers = await authHeaders();
  const r = await fetch(`${base}${path}`, {
    method: "POST",
    headers,
    body: JSON.stringify(body),
  });
  if (!r.ok) {
    const t = await r.text();
    throw new Error(`${r.status}: ${t.slice(0, 400)}`);
  }
  return r.json() as Promise<T>;
}
