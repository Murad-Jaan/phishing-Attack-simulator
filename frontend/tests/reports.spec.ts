import { test, expect, type Page } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

import { openDemoAdmin, storageStatePath } from './support/auth';
import { waitForTheme } from './support/theme';

test.use({ storageState: storageStatePath('admin1') });

async function expectNoSeriousA11y(page: Page): Promise<void> {
  const results = await new AxeBuilder({ page }).analyze();
  const violations = results.violations.filter(
    (violation) => violation.impact === 'serious' || violation.impact === 'critical',
  );
  expect(violations).toEqual([]);
}

test('reports controls, definitions and charts pass axe in light and dark themes', async ({
  page,
}) => {
  await openDemoAdmin(page);
  await page.goto('/reports');

  await expect(page.getByRole('heading', { level: 1, name: 'Reports' })).toBeVisible();
  await expect(page.getByTestId('reports-campaign')).toBeVisible();
  await expect(page.getByTestId('reports-export')).toBeVisible();
  await expect(page.getByText('How these numbers work')).toBeVisible();
  await expect(page.getByText('Minimum group size')).toBeVisible();

  await expectNoSeriousA11y(page);
  await page.getByTestId('theme-toggle').click();
  await waitForTheme(page, 'dark');
  await expectNoSeriousA11y(page);
});

test('dashboard renders four metrics and its trend table in light and dark themes', async ({
  page,
}) => {
  await openDemoAdmin(page);

  await expect(page.getByRole('heading', { level: 1, name: 'Dashboard' })).toBeVisible();
  await expect(page.getByTestId('dashboard-metric')).toHaveCount(4);
  await expect(
    page.getByRole('heading', { name: 'Click-rate trend' }),
  ).toBeVisible();

  await expectNoSeriousA11y(page);
  await page.getByTestId('theme-toggle').click();
  await waitForTheme(page, 'dark');
  await expectNoSeriousA11y(page);
});
