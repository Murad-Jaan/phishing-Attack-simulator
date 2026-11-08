import { test, expect, type Page } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

test.describe.configure({ mode: 'serial' });

const DEMO_ADMIN_EMAIL = 'demo-admin-1@example.test';

async function loginAsDemoAdmin(page: Page): Promise<void> {
  const password = process.env.DEMO_ADMIN_1_PASSWORD ?? '';
  expect(
    password,
    'DEMO_ADMIN_1_PASSWORD must be provided at run time (never committed) and `make seed` must have run on the dev DB',
  ).toMatch(/^\S{12,}$/);
  await page.goto('/login');
  await page.getByTestId('login-email').fill(DEMO_ADMIN_EMAIL);
  await page.getByTestId('login-password').fill(password);
  await page.getByTestId('login-submit').click();
  await page.waitForURL('/');
}

async function expectNoSeriousA11y(page: Page): Promise<void> {
  const results = await new AxeBuilder({ page }).analyze();
  const violations = results.violations.filter(
    (violation) => violation.impact === 'serious' || violation.impact === 'critical',
  );
  expect(violations).toEqual([]);
}

test.describe('Authenticated shell and dashboard', () => {
  test.beforeEach(async ({ page }) => {
    await loginAsDemoAdmin(page);
  });

  test('authenticated shell and dashboard have no serious accessibility issues in light theme', async ({
    page,
  }) => {
    await expectNoSeriousA11y(page);
  });

  test('authenticated shell and dashboard have no serious accessibility issues in dark theme', async ({
    page,
  }) => {
    await page.getByTestId('theme-toggle').click();
    await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark');
    await expectNoSeriousA11y(page);
  });

  test('every sidebar link loads a page with exactly one h1 and marks itself current', async ({
    page,
  }) => {
    const nav = page.getByRole('navigation', { name: 'Main navigation' });
    const links = await nav.getByRole('link').evaluateAll((elements) =>
      elements.map((element) => ({
        href: element.getAttribute('href') ?? '',
        name: (element.textContent ?? '').trim(),
      })),
    );

    expect(links.map((link) => link.name)).toEqual([
      'Dashboard',
      'Campaigns',
      'Templates',
      'Groups',
      'Reports',
      'Mail Analyzer',
      'Settings',
    ]);

    for (const link of links) {
      await page.goto(link.href);
      await expect(page.locator('h1')).toHaveCount(1);
      await expect(page.locator('h1')).toHaveText(link.name);
      await expect(nav.getByRole('link', { name: link.name })).toHaveAttribute(
        'aria-current',
        'page',
      );
    }
  });

  test('admin sees Settings and the seeded read-only values', async ({ page }) => {
    const settingsLink = page
      .getByRole('navigation', { name: 'Main navigation' })
      .getByRole('link', { name: 'Settings' });
    await expect(settingsLink).toBeVisible();
    await settingsLink.click();
    await expect(page).toHaveURL(/\/settings$/);
    await expect(page.getByRole('heading', { level: 1 })).toHaveText('Settings');
    await expect(page.getByText('Read-only view')).toBeVisible();

    for (const value of [
      'Demo Organization',
      'example.test',
      'UTC',
      '90 days',
      '5 people',
      'example.com',
      '*.test',
      '*.invalid',
    ]) {
      await expect(page.getByText(value, { exact: true })).toBeVisible();
    }

    await expect(page.locator('main input, main textarea, main select')).toHaveCount(0);
    await expect(page.locator('main form')).toHaveCount(0);
    await expect(
      page.locator('main').getByRole('button', { name: /save|edit/i }),
    ).toHaveCount(0);
  });

  test('keyboard users get a working skip link, logical tab order, and aria-current', async ({
    page,
  }) => {
    const skip = page.getByRole('link', { name: 'Skip to main content' });

    await page.goto('/');
    await page.keyboard.press('Tab');
    await expect(skip).toBeFocused();
    await page.keyboard.press('Enter');
    await expect(page.locator('#main-content')).toBeFocused();

    await page.goto('/');
    await page.keyboard.press('Tab');
    await expect(skip).toBeFocused();
    await page.keyboard.press('Tab');
    await expect(
      page.getByRole('link', { name: 'Phishing Simulation + Detection' }).first(),
    ).toBeFocused();
    await page.keyboard.press('Tab');
    const dashboard = page
      .getByRole('navigation', { name: 'Main navigation' })
      .getByRole('link', { name: 'Dashboard' });
    await expect(dashboard).toBeFocused();
    await expect(dashboard).toHaveAttribute('aria-current', 'page');
  });

  test('mobile drawer opens, Escape closes it, and focus returns to the menu button', async ({
    page,
  }) => {
    await page.setViewportSize({ width: 390, height: 844 });

    const menu = page.locator('button[aria-controls="app-sidebar"]');
    await expect(menu).toBeVisible();
    await expect(menu).toHaveAttribute('aria-expanded', 'false');
    await expect(menu).toHaveAttribute('aria-label', 'Open menu');

    await menu.click();
    await expect(menu).toHaveAttribute('aria-expanded', 'true');
    await expect(menu).toHaveAttribute('aria-label', 'Close menu');
    await expect(page.locator('#app-sidebar')).toBeVisible();

    await page.keyboard.press('Escape');
    await expect(menu).toHaveAttribute('aria-expanded', 'false');
    await expect(menu).toHaveAttribute('aria-label', 'Open menu');
    await expect(page.locator('#app-sidebar')).not.toBeVisible();
    await expect(menu).toBeFocused();
  });
});
