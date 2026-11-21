import { test, expect, type Page } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

import { storageStatePath } from './support/auth';

async function openAnalyzer(page: Page): Promise<void> {
  await page.goto('/analyzer');
  await expect(page.getByRole('heading', { level: 1, name: 'Mail Analyzer' })).toBeVisible();
  await expect(page.getByTestId('analyzer-submit')).toBeVisible();
}

function criticalViolations(results: {
  violations: Array<{ impact?: string | null }>;
}) {
  return results.violations.filter(
    (violation) => violation.impact === 'serious' || violation.impact === 'critical',
  );
}

const EML = [
  'From: "PayPal" <service@paypa1-support.com>',
  'Reply-To: <collect@evil.test>',
  'Authentication-Results: mx; spf=fail; dkim=fail; dmarc=fail',
  'Subject: Urgent verify your password',
  '',
  '<a href="http://evil-login.test/x">https://paypal.com/login</a>',
  'Dear Customer, act now.',
].join('\n');

test.describe('Mail analyzer', () => {
  test.use({ storageState: storageStatePath('admin1') });

  test('analyzes a pasted sample, shows reasons and saves the verdict', async ({ page }) => {
    await openAnalyzer(page);

    await page.getByTestId('analyzer-load-sample').click();
    await page.getByTestId('analyzer-consent').check();
    await page.getByTestId('analyzer-submit').click();

    await expect(page.getByTestId('analyzer-result')).toBeVisible();
    await expect(page.getByTestId('analyzer-label')).toHaveText('Likely phishing');
    await expect(page.getByTestId('analyzer-score')).toContainText('/100');
    const meter = page.getByTestId('analyzer-meter');
    await expect(meter).toHaveAttribute('aria-valuemin', '0');
    await expect(meter).toHaveAttribute('aria-valuemax', '100');
    await expect(meter).toHaveAttribute('aria-valuetext', /Likely phishing, \d+ of 100/);
    await expect(page.getByTestId('analyzer-findings')).toContainText('S-03');
    await expect(page.getByTestId('analyzer-findings')).toContainText('S-11');
    await expect(page.getByTestId('analyzer-actions')).toContainText('Do not click');
    await expect(page.getByTestId('analyzer-links')).toContainText('paypa1-verify.com');
    await expect(page.getByTestId('analyzer-links').getByRole('link')).toHaveCount(0);

    await page.getByTestId('analyzer-report').click();
    await expect(page.getByTestId('analyzer-reported')).toBeVisible();
  });

  test('requires consent and an email file before submitting', async ({ page }) => {
    await openAnalyzer(page);

    await page.getByTestId('analyzer-submit').click();
    await expect(page.getByRole('alert').filter({ hasText: 'Analysis failed' })).toContainText(
      'Consent is required before analyzing a message.',
    );

    await page.getByTestId('analyzer-tab-upload').click();
    await page.getByTestId('analyzer-consent').check();
    await page.getByTestId('analyzer-submit').click();
    await expect(page.getByRole('alert').filter({ hasText: 'Analysis failed' })).toContainText(
      'Choose an .eml file to analyze.',
    );
  });

  test('analyzes an uploaded .eml file', async ({ page }) => {
    await openAnalyzer(page);
    await page.getByTestId('analyzer-tab-upload').click();
    await page.getByTestId('analyzer-file').setInputFiles({
      name: 'message.eml',
      mimeType: 'message/rfc822',
      buffer: Buffer.from(EML),
    });
    await page.getByTestId('analyzer-consent').check();
    await page.getByTestId('analyzer-submit').click();

    await expect(page.getByTestId('analyzer-result')).toBeVisible();
    await expect(page.getByTestId('analyzer-label')).toHaveText('Likely phishing');
    await expect(page.getByTestId('analyzer-findings')).toContainText('E-02');
    await expect(page.getByTestId('analyzer-findings')).toContainText('E-05');
    await expect(page.getByTestId('analyzer-findings')).toContainText('E-07');
  });

  test('analyzer page should not have serious or critical accessibility issues in light mode', async ({
    page,
  }) => {
    await openAnalyzer(page);
    await page.getByTestId('analyzer-load-sample').click();
    await page.getByTestId('analyzer-consent').check();
    await page.getByTestId('analyzer-submit').click();
    await expect(page.getByTestId('analyzer-result')).toBeVisible();

    const results = await new AxeBuilder({ page }).analyze();
    expect(criticalViolations(results)).toEqual([]);
  });

  test('analyzer result should not have serious or critical accessibility issues in dark mode', async ({
    page,
  }) => {
    await page.emulateMedia({ colorScheme: 'dark' });
    await openAnalyzer(page);
    await page.getByTestId('analyzer-load-sample').click();
    await page.getByTestId('analyzer-consent').check();
    await page.getByTestId('analyzer-submit').click();
    await expect(page.getByTestId('analyzer-result')).toBeVisible();

    const results = await new AxeBuilder({ page }).analyze();
    expect(criticalViolations(results)).toEqual([]);
  });
});
