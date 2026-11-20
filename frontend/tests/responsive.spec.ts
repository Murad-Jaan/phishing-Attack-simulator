import { test, expect, type Page } from '@playwright/test';

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

const VIEWPORTS = [320, 768, 1440] as const;

async function expectNoHorizontalScroll(page: Page, path: string, width: number) {
  const metrics = await page.evaluate(() => ({
    scrollWidth: document.documentElement.scrollWidth,
    clientWidth: document.documentElement.clientWidth,
  }));
  expect(
    metrics.scrollWidth,
    `${path} should not overflow horizontally at ${width}px`,
  ).toBeLessThanOrEqual(metrics.clientWidth + 1);
}

async function visit(page: Page, target: PageTarget, width: number) {
  await page.setViewportSize({ width, height: 900 });
  await page.goto(target.path);
  await page.waitForLoadState('networkidle');
  await expect(
    page.getByRole('heading', { level: 1, name: target.heading, exact: true }),
  ).toBeVisible();
  await expectNoHorizontalScroll(page, target.path, width);
}

test.describe('Responsive public pages', () => {
  for (const target of PUBLIC_PAGES) {
    for (const width of VIEWPORTS) {
      test(`${target.path} is usable at ${width}px`, async ({ page }) => {
        await visit(page, target, width);
      });
    }
  }
});

test.describe('Responsive authenticated pages', () => {
  test.use({ storageState: storageStatePath('admin1') });

  for (const target of APP_PAGES) {
    for (const width of VIEWPORTS) {
      test(`${target.path} is usable at ${width}px`, async ({ page }) => {
        await visit(page, target, width);
      });
    }
  }

  test('sidebar becomes a drawer on small screens', async ({ page }) => {
    await page.setViewportSize({ width: 320, height: 760 });
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    const sidebar = page.locator('#app-sidebar');
    await expect(sidebar).toBeHidden();
    await page.getByRole('button', { name: 'Open menu' }).click();
    await expect(sidebar).toBeVisible();
    await page.keyboard.press('Escape');
    await expect(sidebar).toBeHidden();
  });

  test('sidebar stays a fixed column on desktop', async ({ page }) => {
    await page.setViewportSize({ width: 1024, height: 760 });
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    await expect(page.locator('#app-sidebar')).toBeVisible();
    await expect(page.getByRole('button', { name: 'Open menu' })).toBeHidden();
  });

  test('primary controls meet the 44px touch target at 320px', async ({ page }) => {
    await page.setViewportSize({ width: 320, height: 760 });
    await page.goto('/campaigns');
    await page.waitForLoadState('networkidle');

    const undersized = await page
      .locator(
        'main button:visible, main a[class*="inline-flex"]:visible, #app-sidebar button:visible, #app-sidebar a[class*="inline-flex"]:visible, header button:visible',
      )
      .evaluateAll((elements) =>
        elements
          .map((element) => {
            const rect = element.getBoundingClientRect();
            return {
              label: element.textContent?.trim().slice(0, 48) || element.tagName,
              width: Math.round(rect.width),
              height: Math.round(rect.height),
            };
          })
          .filter((item) => item.width > 0 && item.height > 0)
          .filter((item) => item.width < 44 || item.height < 44),
      );

    expect(undersized).toEqual([]);
  });
});
