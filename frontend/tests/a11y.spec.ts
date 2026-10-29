import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

test.describe('Accessibility baseline', () => {
  test('homepage should not have any automatically detectable accessibility issues', async ({
    page,
  }: any) => {
    await page.goto('/');
    const accessibilityScanResults = await new AxeBuilder({ page }).analyze();
    const violations = accessibilityScanResults.violations.filter(
      (v) => v.impact === 'serious' || v.impact === 'critical'
    );
    expect(violations).toEqual([]);
  });

  test('/login should not have serious or critical accessibility issues', async ({
    page,
  }: any) => {
    await page.goto('/login');
    const accessibilityScanResults = await new AxeBuilder({ page }).analyze();
    const violations = accessibilityScanResults.violations.filter(
      (v) => v.impact === 'serious' || v.impact === 'critical'
    );
    expect(violations).toEqual([]);
  });
});
