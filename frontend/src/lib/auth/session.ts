import { cookies } from 'next/headers';

const FORWARDED_COOKIE_NAMES = [
  'phishsim_session',
  'phishsim_csrf',
  '__Host-phishsim_session',
  '__Host-phishsim_csrf',
];

export interface SessionUser {
  id: string;
  email: string;
  display_name: string;
  role: string;
  org_id: string;
}

export async function getSessionUser(): Promise<SessionUser | null> {
  const cookieStore = await cookies();
  const forwarded = FORWARDED_COOKIE_NAMES.filter((name) => cookieStore.has(name))
    .map((name) => `${name}=${cookieStore.get(name)?.value ?? ''}`)
    .join('; ');
  if (!forwarded) {
    return null;
  }
  const api = process.env.API_INTERNAL_URL || 'http://127.0.0.1:8000';
  const res = await fetch(`${api}/api/v1/auth/me`, {
    headers: { cookie: forwarded },
    cache: 'no-store',
  });
  if (!res.ok) {
    return null;
  }
  const data = (await res.json()) as { user?: SessionUser };
  if (!data.user) {
    return null;
  }
  return data.user;
}
