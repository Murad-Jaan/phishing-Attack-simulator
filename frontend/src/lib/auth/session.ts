import { cache } from 'react';
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

export async function getForwardedCookieHeader(): Promise<string> {
  const cookieStore = await cookies();
  return FORWARDED_COOKIE_NAMES.filter((name) => cookieStore.has(name))
    .map((name) => `${name}=${cookieStore.get(name)?.value ?? ''}`)
    .join('; ');
}

export const getSessionUser = cache(async (): Promise<SessionUser | null> => {
  const forwarded = await getForwardedCookieHeader();
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
});
