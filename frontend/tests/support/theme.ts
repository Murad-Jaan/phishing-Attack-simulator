import { expect, type Page } from '@playwright/test';

export async function setDarkTheme(page: Page): Promise<void> {
  await page.evaluate(() => document.documentElement.classList.add('dark'));
  await expect
    .poll(() =>
      page.evaluate(() =>
        getComputedStyle(document.documentElement).getPropertyValue('--text').trim(),
      ),
    )
    .toBe('#f7f2f3');
}
