import { getForwardedCookieHeader } from '@/lib/auth/session';
import type { DashboardData } from '@/lib/api/reports-types';

async function api<T>(path: string): Promise<T | null> {
  const cookie = await getForwardedCookieHeader();
  if (!cookie) {
    return null;
  }
  const apiBase = process.env.API_INTERNAL_URL || 'http://127.0.0.1:8000';
  const response = await fetch(`${apiBase}${path}`, {
    headers: { cookie },
    cache: 'no-store',
  });
  if (!response.ok) {
    return null;
  }
  return (await response.json()) as T;
}

export async function getDashboard(): Promise<DashboardData | null> {
  return api<DashboardData>('/api/v1/dashboard');
}
