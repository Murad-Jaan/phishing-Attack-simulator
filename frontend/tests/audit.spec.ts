import { test, expect, type Page } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

import { storageStatePath } from './support/auth';

test.use({ storageState: storageStatePath('admin1') });

function seriousViolations(violations: { impact?: string | null }[]) {
  return violations.filter((v) => v.impact === 'serious' || v.impact === 'critical');
}

test('admin opens the audit log, filters, exports CSV and has no serious a11y issues', async ({
  page,
}: {
  page: Page;
}) => {
  await page.goto('/settings');
  await page.getByRole('link', { name: 'Open audit log' }).click();
  await expect(page).toHaveURL(/\/settings\/audit$/);
  await expect(page.getByRole('heading', { level: 1 })).toHaveText('Audit log');

  await page.getByLabel('Action').fill('campaign.');
  await page.getByRole('button', { name: 'Apply filters' }).click();
  await expect(page.getByRole('heading', { name: /events?$/ })).toBeVisible();

  const downloadPromise = page.waitForEvent('download');
  await page.getByTestId('audit-export').click();
  const download = await downloadPromise;
  expect(download.suggestedFilename()).toBe('audit-log.csv');

  const results = await new AxeBuilder({ page }).analyze();
  expect(seriousViolations(results.violations)).toEqual([]);
});
