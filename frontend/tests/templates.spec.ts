import { test, expect, type Page } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

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

async function openTemplates(page: Page): Promise<void> {
  await loginAsDemoAdmin(page);
  await page.goto('/templates');
  await expect(page.getByTestId('template-results')).toBeVisible();
  await expect(page.getByTestId('template-grid')).toBeVisible();
}

function criticalViolations(results: {
  violations: Array<{ impact?: string | null }>;
}) {
  return results.violations.filter(
    (violation) => violation.impact === 'serious' || violation.impact === 'critical',
  );
}

test.describe('Template library', () => {
  test('filters templates, previews red flags, switches viewport and closes on Escape', async ({
    page,
  }) => {
    await openTemplates(page);

    await expect(page.getByTestId('template-count')).toContainText('templates');

    await page.getByTestId('template-search').fill('SC-01');
    await expect(page.getByTestId('template-count')).toHaveText('1 template');
    await expect(
      page.getByRole('heading', { name: 'SC-01: Account suspension warning' }),
    ).toBeVisible();

    await page.getByTestId('template-search').fill('salary');
    await expect(page.getByTestId('template-count')).toHaveText('1 template');
    await expect(
      page.getByRole('heading', { name: 'SC-06: Shared salary review' }),
    ).toBeVisible();

    await page.getByTestId('template-search').fill('SC-01');
    await expect(
      page.getByRole('heading', { name: 'SC-01: Account suspension warning' }),
    ).toBeVisible();
    await expect(page.getByTestId('template-count')).toHaveText('1 template');
    await page.getByRole('button', { name: 'Preview' }).click();

    const dialog = page.getByRole('dialog', { name: 'SC-01: Account suspension warning' });
    await expect(dialog).toBeVisible();
    await expect(page.getByTestId('red-flags-panel')).toContainText('Urgency and threat');
    await expect(page.getByTestId('template-preview-content')).toContainText(
      'Your account will be suspended',
    );

    await page.getByTestId('viewport-mobile').click();
    await expect(page.getByTestId('preview-viewport')).toHaveAttribute(
      'data-viewport',
      'mobile',
    );

    await page.getByTestId('red-flags-toggle').uncheck();
    await expect(page.getByTestId('red-flags-panel')).toHaveCount(0);

    await page.getByTestId('red-flags-toggle').check();
    await expect(page.getByTestId('red-flags-panel')).toContainText('Urgency and threat');

    await page.keyboard.press('Escape');
    await expect(dialog).toHaveCount(0);
  });

  test('templates page should not have serious or critical accessibility issues in light mode', async ({
    page,
  }) => {
    await openTemplates(page);
    const results = await new AxeBuilder({ page }).analyze();
    expect(criticalViolations(results)).toEqual([]);
  });

  test('template preview dialog should not have serious or critical accessibility issues in dark mode', async ({
    page,
  }) => {
    await page.emulateMedia({ colorScheme: 'dark' });
    await openTemplates(page);
    await page.getByTestId('template-search').fill('SC-01');
    await expect(
      page.getByRole('heading', { name: 'SC-01: Account suspension warning' }),
    ).toBeVisible();
    await expect(page.getByTestId('template-count')).toHaveText('1 template');
    await page.getByRole('button', { name: 'Preview' }).click();
    await expect(page.getByTestId('template-preview-content')).toBeVisible();

    const results = await new AxeBuilder({ page }).analyze();
    expect(criticalViolations(results)).toEqual([]);
  });
});
