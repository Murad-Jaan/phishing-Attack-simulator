import { test, expect, type Page } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

import { storageStatePath } from './support/auth';

interface PageTarget {
  path: string;
  heading: string;
}

const PUBLIC_PAGES: PageTarget[] = [
  { path: '/login', heading: 'Welcome back' },
  { path: '/signup', heading: 'Request access' },
  { path: '/learn/demo-token', heading: 'This was a phishing simulation' },
  { path: '/learn/demo-token/quiz', heading: 'Quick security check' },
];

const APP_PAGES: PageTarget[] = [
  { path: '/', heading: 'Dashboard' },
  { path: '/campaigns', heading: 'Campaigns' },
  { path: '/templates', heading: 'Templates' },
  { path: '/groups', heading: 'Groups' },
  { path: '/reports', heading: 'Reports' },
  { path: '/analyzer', heading: 'Mail Analyzer' },
  { path: '/settings', heading: 'Settings' },
  { path: '/settings/audit', heading: 'Audit log' },
];

async function expectNoSeriousA11y(page: Page, target: PageTarget, theme: 'light' | 'dark') {
  await page.emulateMedia({ colorScheme: theme });
  await page.goto(target.path);
  await page.waitForLoadState('networkidle');
  await expect(
    page.getByRole('heading', { level: 1, name: target.heading, exact: true }),
  ).toBeVisible();

  const results = await new AxeBuilder({ page }).analyze();
  const violations = results.violations.filter(
    (violation) => violation.impact === 'serious' || violation.impact === 'critical',
  );
  expect(violations, `${target.path} (${theme} theme)`).toEqual([]);
}

test.describe('Accessibility across public pages', () => {
  for (const target of PUBLIC_PAGES) {
    for (const theme of ['light', 'dark'] as const) {
      test(`${target.path} has no serious ${theme} violations`, async ({ page }) => {
        await expectNoSeriousA11y(page, target, theme);
      });
    }
  }
});

test.describe('Accessibility across authenticated pages', () => {
  test.use({ storageState: storageStatePath('admin1') });

  for (const target of APP_PAGES) {
    for (const theme of ['light', 'dark'] as const) {
      test(`${target.path} has no serious ${theme} violations`, async ({ page }) => {
        await expectNoSeriousA11y(page, target, theme);
      });
    }
  }
});
