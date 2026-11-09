import { getForwardedCookieHeader } from '@/lib/auth/session';

export interface OrganizationSettings {
  name: string;
  primary_domain: string;
  timezone: string;
  retention_days: number;
  min_group_size: number;
  send_domain_allowlist: string[];
}

export async function getOrganizationSettings(): Promise<OrganizationSettings | null> {
  const cookie = await getForwardedCookieHeader();
  if (!cookie) {
    return null;
  }

  const api = process.env.API_INTERNAL_URL || 'http://127.0.0.1:8000';
  const res = await fetch(`${api}/api/v1/settings/organization`, {
    headers: { cookie },
    cache: 'no-store',
  });
  if (!res.ok) {
    return null;
  }

  const data = (await res.json()) as { settings?: OrganizationSettings };
  return data.settings ?? null;
}
