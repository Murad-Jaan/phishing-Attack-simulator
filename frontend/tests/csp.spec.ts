import { test, expect } from '@playwright/test';

const PROD_BASE_URL =
  process.env.PROD_BASE_URL ??
  (process.env.CI ? 'http://127.0.0.1:3000' : 'http://127.0.0.1:3001');

test('production CSP on /login keeps a nonce and strict-dynamic with a dark theme cookie', async ({
  browser,
}) => {
  const context = await browser.newContext();
  await context.addCookies([{ name: 'phishsim_theme', value: 'dark', url: PROD_BASE_URL }]);
  const page = await context.newPage();

  const response = await page.goto(`${PROD_BASE_URL}/login`);
  expect(response?.status()).toBe(200);

  const csp = response?.headers()['content-security-policy'] ?? '';
  expect(csp).toMatch(/script-src [^;]*'nonce-[^']+'[^;]*'strict-dynamic'/);
  expect(csp).not.toContain('unsafe-inline');
  expect(csp).not.toContain('unsafe-eval');

  await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark');
  await context.close();
});
