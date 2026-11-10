import { test, expect, type Page } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

async function expectNoSeriousA11y(page: Page): Promise<void> {
  const results = await new AxeBuilder({ page }).analyze();
  const violations = results.violations.filter(
    (violation) => violation.impact === 'serious' || violation.impact === 'critical',
  );
  expect(violations).toEqual([]);
}

test.describe('Login theme and links', () => {
  test('login has no serious or critical accessibility issues in light theme', async ({ page }) => {
    await page.goto('/login');
    await expectNoSeriousA11y(page);
  });

  test('login has no serious or critical accessibility issues in dark theme', async ({ page }) => {
    await page.goto('/login');
    await page.getByTestId('theme-toggle').click();
    await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark');
    await expectNoSeriousA11y(page);
  });

  test('theme toggle sets the phishsim_theme cookie and survives a reload', async ({
    page,
    context,
  }) => {
    await page.goto('/login');
    await page.getByTestId('theme-toggle').click();
    await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark');

    const darkCookie = (await context.cookies()).find(
      (cookie) => cookie.name === 'phishsim_theme',
    );
    expect(darkCookie?.value).toBe('dark');

    await page.reload();
    await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark');
    const reloadedCookie = (await context.cookies()).find(
      (cookie) => cookie.name === 'phishsim_theme',
    );
    expect(reloadedCookie?.value).toBe('dark');
  });

  test('forgot-password link is absent while the flag is false and Sign up goes to /signup', async ({
    page,
  }) => {
    await page.goto('/login');
    await expect(page.getByRole('link', { name: 'Forgot password?' })).toHaveCount(0);

    const signUp = page.getByTestId('signup-link');
    await expect(signUp).toBeVisible();
    await expect(signUp).toHaveAttribute('href', '/signup');
    await signUp.click();
    await expect(page).toHaveURL(/\/signup$/);
    await expect(page.getByRole('heading', { level: 1 })).toHaveText('Request access');
  });
});
