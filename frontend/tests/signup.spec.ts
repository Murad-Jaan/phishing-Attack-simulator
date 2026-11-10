import { test, expect, type Page } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

async function expectNoSeriousA11y(page: Page): Promise<void> {
  const results = await new AxeBuilder({ page }).analyze();
  const violations = results.violations.filter(
    (violation) => violation.impact === 'serious' || violation.impact === 'critical',
  );
  expect(violations).toEqual([]);
}

test.describe('Sign-up request access page', () => {
  test('shows the request-access heading and a working back link', async ({ page }) => {
    await page.goto('/signup');
    await expect(page.getByRole('heading', { level: 1 })).toHaveText('Request access');

    const back = page.getByRole('link', { name: 'Back to sign in' });
    await expect(back).toHaveAttribute('href', '/login');
    await back.click();
    await expect(page).toHaveURL(/\/login$/);
    await expect(page.getByRole('heading', { level: 1 })).toHaveText('Welcome back');
  });

  test('has no serious or critical accessibility issues in light and dark themes', async ({
    page,
  }) => {
    await page.goto('/signup');
    await expectNoSeriousA11y(page);

    await page.getByTestId('theme-toggle').click();
    await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark');
    await expectNoSeriousA11y(page);
  });
});
