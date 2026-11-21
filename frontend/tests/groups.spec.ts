import { test, expect, type Page } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

import { openDemoAdmin, storageStatePath } from './support/auth';
import { setDarkTheme } from './support/theme';

async function createGroup(page: Page): Promise<string> {
  const name = `Playwright Group ${Date.now()}`;
  await page.getByTestId('new-group').click();
  await page.getByTestId('group-name').fill(name);
  await page.getByTestId('group-department').fill('Quality');
  await page.getByTestId('group-description').fill('Created by the Playwright happy path');
  await page.getByTestId('create-group').click();
  await expect(page.getByTestId('group-detail')).toContainText(name);
  await expect(page.getByTestId('group-list')).toContainText(name);
  return name;
}

function seriousViolations(violations: { impact?: string | null }[]) {
  return violations.filter((v) => v.impact === 'serious' || v.impact === 'critical');
}

test.describe('Target groups', () => {
  test.use({ storageState: storageStatePath('admin1') });

  test('happy path: create group, add user, import CSV with a row error and suppression warning', async ({
    page,
  }: any) => {
    await openDemoAdmin(page);
    await page.goto('/groups');
    await createGroup(page);

    const stamp = Date.now();
    const member = `pw-member-${stamp}@example.test`;
    await page.getByTestId('member-email').fill(member);
    await page.getByTestId('member-name').fill('Playwright Member');
    await page.getByTestId('add-user').click();
    await expect(page.getByTestId('group-detail')).toContainText(member);

    const csv = [
      'email,display_name',
      `pw-csv-${stamp}@example.test,CSV Member`,
      'bad-email,Broken Row',
    ].join('\n');
    await page.getByTestId('csv-file').setInputFiles({
      name: 'targets.csv',
      mimeType: 'text/csv',
      buffer: Buffer.from(csv, 'utf8'),
    });
    await page.getByTestId('import-csv').click();

    const result = page.getByTestId('import-result');
    await expect(result).toBeVisible();
    await expect(result).toContainText('Imported 1 of 2');
    await expect(result).toContainText('invalid email');
    await expect(page.getByTestId('group-detail')).toContainText(`pw-csv-${stamp}@example.test`);

    const warning = page.getByTestId('suppression-warning');
    await expect(warning).toBeVisible();
    await expect(warning).toContainText('This group has 2 members');
    await expect(warning).toContainText('at least 5 members');
  });

  test('groups page has no serious or critical axe issues in light mode', async ({
    page,
  }: any) => {
    await openDemoAdmin(page);
    await page.goto('/groups');
    await createGroup(page);
    const results = await new AxeBuilder({ page }).analyze();
    expect(seriousViolations(results.violations)).toEqual([]);
  });

  test('groups page has no serious or critical axe issues in dark mode', async ({
    page,
  }: any) => {
    await openDemoAdmin(page);
    await page.goto('/groups');
    await createGroup(page);
    await setDarkTheme(page);
    const results = await new AxeBuilder({ page }).analyze();
    expect(seriousViolations(results.violations)).toEqual([]);
  });
});
