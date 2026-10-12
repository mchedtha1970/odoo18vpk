import { apiUrl } from '../config/odoo';

export type SessionUser = { id: number; login: string; name: string };

export type AppSession = {
  sessionId: string;
  user: SessionUser;
};

let active: AppSession | null = null;

export function setActiveSession(session: AppSession | null) {
  active = session;
}

export async function api<T>(path: string, options: { method?: string; body?: unknown } = {}): Promise<T> {
  const headers: Record<string, string> = { Accept: 'application/json' };
  if (active?.sessionId) {
    headers['X-Session-Id'] = active.sessionId;
  }
  if (options.body !== undefined) {
    headers['Content-Type'] = 'application/json';
  }
  const response = await fetch(apiUrl(path), {
    method: options.method || 'GET',
    headers,
    body: options.body !== undefined ? JSON.stringify(options.body) : undefined,
  });
  const data = (await response.json().catch(() => ({}))) as { ok?: boolean; error?: string };
  if (!response.ok || data.ok === false) {
    throw new Error(data.error || 'ขอข้อมูลไม่สำเร็จ');
  }
  return data as T;
}
