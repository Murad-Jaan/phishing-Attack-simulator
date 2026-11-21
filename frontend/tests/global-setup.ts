import { mkdir } from 'node:fs/promises';
import path from 'node:path';

import { chromium, type FullConfig } from '@playwright/test';

import {
  DEMO_ACCOUNTS,
  demoAdminEmail,
  passwordEnvVar,
  storageStatePath,
} from './support/auth';

export default async function globalSetup(config: FullConfig): Promise<void> {
  const baseURL = config.projects[0]?.use.baseURL;

  if (!baseURL) {
    throw new Error('Playwright baseURL is required to create the demo admin auth states.');
  }

  const browser = await chromium.launch();

  try {
    for (const account of DEMO_ACCOUNTS) {
      const envVar = passwordEnvVar(account);
      const password = process.env[envVar] ?? '';

      if (!/^\S{12,}$/.test(password)) {
        throw new Error(
          `${envVar} must be provided at run time (never committed) and \`make seed\` must have run on the dev DB`,
        );
      }

      const context = await browser.newContext({ baseURL });
      const page = await context.newPage();

      await page.goto('/login');
      await page.getByTestId('login-email').fill(demoAdminEmail(account));
      await page.getByTestId('login-password').fill(password);
      await page.getByTestId('login-submit').click();
      await page.waitForURL('/');

      const statePath = storageStatePath(account);
      await mkdir(path.dirname(statePath), { recursive: true });
      await context.storageState({ path: statePath });
      await context.close();
    }
  } finally {
    await browser.close();
  }
}
