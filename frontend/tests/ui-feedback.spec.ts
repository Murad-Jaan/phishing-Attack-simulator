import { test, expect } from '@playwright/test';

import { storageStatePath } from './support/auth';

test.use({ storageState: storageStatePath('admin1') });

test('saving a group shows a non-blocking success toast', async ({ page }) => {
  await page.goto('/groups');
  await page.waitForLoadState('networkidle');

  await page.getByTestId('new-group').click();
  await page.getByTestId('group-name').fill(`Toast Group ${Date.now()}`);
  await page.getByTestId('create-group').click();

  const toast = page.getByTestId('toast').filter({ hasText: 'Group saved.' });
  await expect(toast).toBeVisible();
});
