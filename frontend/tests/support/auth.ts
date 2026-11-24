import { readFileSync } from 'node:fs';
import path from 'node:path';

import type { BrowserContext, Page } from '@playwright/test';

export const DEMO_ADMIN_EMAILS = {
  admin1: 'demo-admin-1@example.test',
  admin2: 'demo-admin-2@example.test',
} as const;

export const DEMO_ACCOUNTS = ['admin1', 'admin2'] as const;

export type DemoAccount = (typeof DEMO_ACCOUNTS)[number];

const AUTH_DIR = path.resolve(__dirname, '..', '..', '.playwright', 'auth');

export function passwordEnvVar(account: DemoAccount): string {
  return account === 'admin1' ? 'DEMO_ADMIN_1_PASSWORD' : 'DEMO_ADMIN_2_PASSWORD';
}

export function storageStatePath(account: DemoAccount): string {
  return path.join(AUTH_DIR, `${account}.json`);
}

export function demoAdminEmail(account: DemoAccount): string {
  return DEMO_ADMIN_EMAILS[account];
}

export async function openDemoAdmin(page: Page): Promise<void> {
  await page.goto('/');
  await page.waitForURL('/');
}

export async function switchDemoAdmin(page: Page, account: DemoAccount): Promise<void> {
  const state = JSON.parse(readFileSync(storageStatePath(account), 'utf8')) as {
    cookies: Parameters<BrowserContext['addCookies']>[0];
  };

  await page.context().clearCookies();
  await page.context().addCookies(state.cookies);
  await page.goto('/');
  await page.waitForURL('/');
}
