import { test, expect, type Page } from '@playwright/test';

import { storageStatePath } from './support/auth';

function maxMs(value: string): number {
  return Math.max(
    ...value.split(',').map((part) => {
      const trimmed = part.trim();
      const numeric = Number.parseFloat(trimmed) || 0;
      return trimmed.endsWith('ms') ? numeric : numeric * 1000;
    }),
  );
}

async function motionValues(page: Page, selector: string) {
  return page.locator(selector).first().evaluate((element) => {
    const style = getComputedStyle(element);
    return {
      animationDuration: style.animationDuration,
      animationDelay: style.animationDelay,
      transitionDuration: style.transitionDuration,
      transitionDelay: style.transitionDelay,
    };
  });
}

test.describe('Reduced motion', () => {
  test.use({
    storageState: storageStatePath('admin1'),
    reducedMotion: 'reduce',
  });

  test('route and awareness entrance animations are effectively disabled', async ({ page }) => {
    await page.goto('/');
    await expect(page.getByRole('heading', { level: 1, name: 'Dashboard' })).toBeVisible();
    const route = await motionValues(page, '.page-transition');
    expect(maxMs(route.animationDuration)).toBeLessThanOrEqual(0.1);
    expect(maxMs(route.animationDelay)).toBe(0);

    await page.goto('/learn/demo-token');
    await expect(
      page.getByRole('heading', {
        level: 1,
        name: 'This was a phishing simulation',
      }),
    ).toBeVisible();
    const entrance = await motionValues(page, '.awareness-enter');
    expect(maxMs(entrance.animationDuration)).toBeLessThanOrEqual(0.1);
    expect(maxMs(entrance.animationDelay)).toBe(0);
  });

  test('theme and card transitions are shortened', async ({ page }) => {
    await page.goto('/settings');
    await page.getByTestId('theme-toggle').click();
    await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark');

    const card = await motionValues(page, '.card-lift');
    expect(maxMs(card.transitionDuration)).toBeLessThanOrEqual(0.1);
    expect(maxMs(card.transitionDelay)).toBe(0);

    const body = await page.locator('body').evaluate((element) => {
      const style = getComputedStyle(element);
      return { transitionDuration: style.transitionDuration };
    });
    expect(maxMs(body.transitionDuration)).toBeLessThanOrEqual(0.1);
  });
});
