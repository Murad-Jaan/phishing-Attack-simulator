import { test, expect, type Page } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

const DEMO_ADMIN_EMAIL = 'demo-admin-1@example.test';

async function loginAsDemoAdmin(page: Page): Promise<void> {
  const password = process.env.DEMO_ADMIN_1_PASSWORD ?? '';
  expect(
    password,
    'DEMO_ADMIN_1_PASSWORD must be provided at run time (never committed) and `make seed` must have run on the dev DB'
  ).toMatch(/^\S{12,}$/);
  await page.goto('/login');
  await page.getByTestId('login-email').fill(DEMO_ADMIN_EMAIL);
  await page.getByTestId('login-password').fill(password);
  await page.getByTestId('login-submit').click();
  await page.waitForURL('/');
}

test.describe('Authenticated shell accessibility', () => {
  test('authenticated home shell should not have serious or critical accessibility issues', async ({
    page,
  }: any) => {
    await loginAsDemoAdmin(page);
    const accessibilityScanResults = await new AxeBuilder({ page }).analyze();
    const violations = accessibilityScanResults.violations.filter(
      (v) => v.impact === 'serious' || v.impact === 'critical'
    );
    expect(violations).toEqual([]);
  });
});

test.describe('Login flow', () => {
  test('happy path: login shows display name and role, sign out returns to /login', async ({
    page,
  }: any) => {
    await loginAsDemoAdmin(page);
    await expect(page.getByText('Signed in as')).toBeVisible();
    await expect(page.getByText('Demo Admin 1')).toBeVisible();
    await expect(page.getByText('Role: admin')).toBeVisible();
    await page.getByTestId('sign-out').click();
    await page.waitForURL('/login');
  });

  test('invalid login shows generic error, focused, with preserved email', async ({
    page,
  }: any) => {
    const email = `pw-fail-${Date.now()}@example.test`;
    await page.goto('/login');
    await page.getByTestId('login-email').fill(email);
    await page.getByTestId('login-password').fill('definitely-not-the-password');
    await page.getByTestId('login-submit').click();

    const errorAlert = page.getByTestId('login-error');
    await expect(errorAlert).toBeVisible();
    await expect(errorAlert).toContainText('Email or password is incorrect');
    const focused = await page.evaluate(() => document.activeElement?.getAttribute('data-testid'));
    expect(focused).toBe('login-error');
    await expect(page.getByTestId('login-email')).toHaveValue(email);
  });
});
