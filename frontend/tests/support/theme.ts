import { expect, type Page } from '@playwright/test';

type Theme = 'light' | 'dark';

const THEME_TOKENS: Record<Theme, { text: string; bg: string }> = {
  light: { text: '#0f172a', bg: '#f4f7fc' },
  dark: { text: '#f7f2f3', bg: '#0a0e1a' },
};

/**
 * Waits until the theme class swap has fully settled. The app suppresses
 * transitions while `theme-switching` is present, so waiting for the class to
 * disappear (and for the resolved tokens to flip) prevents axe from scanning a
 * half-transitioned foreground/background pair.
 */
export async function waitForTheme(page: Page, theme: Theme): Promise<void> {
  await expect(page.locator('html')).toHaveAttribute('data-theme', theme);
  await expect(page.locator('html')).not.toHaveClass(/theme-switching/);
  await expect
    .poll(() =>
      page.evaluate(() => {
        const style = getComputedStyle(document.documentElement);
        return {
          text: style.getPropertyValue('--text').trim(),
          bg: style.getPropertyValue('--bg').trim(),
        };
      }),
    )
    .toEqual(THEME_TOKENS[theme]);
}

export async function setDarkTheme(page: Page): Promise<void> {
  await page.evaluate(() => {
    const root = document.documentElement;
    root.classList.add('theme-switching');
    root.classList.remove('light', 'dark');
    root.classList.add('dark');
    root.dataset.theme = 'dark';
    window.setTimeout(() => root.classList.remove('theme-switching'), 260);
  });
  await waitForTheme(page, 'dark');
}
