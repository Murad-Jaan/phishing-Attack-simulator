import { test, expect, type Page, type APIRequestContext } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

import { storageStatePath, switchDemoAdmin } from './support/auth';
import { setDarkTheme } from './support/theme';

test.use({ storageState: storageStatePath('admin1') });
test.setTimeout(300_000);

function resolveMailpitUrl(): string {
  const raw = process.env.MAILPIT_URL ?? 'http://127.0.0.1:8025';
  let url: URL;
  try {
    url = new URL(raw);
  } catch {
    throw new Error(`MAILPIT_URL is not a valid URL: ${raw}`);
  }
  if (url.protocol !== 'http:' && url.protocol !== 'https:') {
    throw new Error(`MAILPIT_URL must use http or https: ${raw}`);
  }
  return url.toString().replace(/\/$/, '');
}

const MAILPIT_URL = resolveMailpitUrl();

function futureMinuteInput(secondsFromNow: number): string {
  return new Date(Date.now() + secondsFromNow * 1000)
    .toISOString()
    .slice(0, 16);
}

async function seedGroup(
  page: Page,
  name: string,
  prefix: string,
  members: number,
): Promise<string> {
  return page.evaluate(
    async ({ name, prefix, members }) => {
      async function csrf(): Promise<string> {
        const res = await fetch('/api/v1/auth/csrf', {
          cache: 'no-store',
          credentials: 'same-origin',
        });
        const data = (await res.json()) as { csrf_token: string };
        return data.csrf_token;
      }
      const token = await csrf();
      const headers = {
        'Content-Type': 'application/json',
        'X-CSRF-Token': token,
      };
      const created = await fetch('/api/v1/groups', {
        method: 'POST',
        credentials: 'same-origin',
        headers,
        body: JSON.stringify({ name, department: 'Quality' }),
      });
      if (!created.ok) {
        throw new Error(`group create failed: ${created.status}`);
      }
      const group = (await created.json()) as { group: { id: string } };
      for (let index = 0; index < members; index += 1) {
        const member = await fetch(`/api/v1/groups/${group.group.id}/members`, {
          method: 'POST',
          credentials: 'same-origin',
          headers,
          body: JSON.stringify({
            email: `${prefix}-${index}@example.test`,
            display_name: `Awareness Target ${index}`,
          }),
        });
        if (!member.ok) {
          throw new Error(`member create failed: ${member.status}`);
        }
      }
      return group.group.id;
    },
    { name, prefix, members },
  );
}

async function seedTemplate(page: Page, name: string): Promise<string> {
  return page.evaluate(
    async ({ name }) => {
      async function csrf(): Promise<string> {
        const res = await fetch('/api/v1/auth/csrf', {
          cache: 'no-store',
          credentials: 'same-origin',
        });
        const data = (await res.json()) as { csrf_token: string };
        return data.csrf_token;
      }
      const token = await csrf();
      const created = await fetch('/api/v1/templates', {
        method: 'POST',
        credentials: 'same-origin',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRF-Token': token,
        },
        body: JSON.stringify({
          name,
          sender: 'Billing Team <billing@vendor.example.test>',
          subject: 'Invoice ready for {{first_name}}',
          body: 'Hello {{first_name}},\n\nOpen {{tracking_link}} to review your invoice.',
          difficulty: 'easy',
          attack_technique_id: 'T1566.002',
          lure_type: 'credential_harvest',
          status: 'published',
          red_flags: [
            {
              label: 'Urgency',
              explanation: 'A short deadline is used to rush the reader.',
            },
          ],
        }),
      });
      if (!created.ok) {
        throw new Error(`template create failed: ${created.status}`);
      }
      const template = (await created.json()) as { template: { id: string } };
      return template.template.id;
    },
    { name },
  );
}

async function createAndLaunch(
  page: Page,
  campaignName: string,
  groupName: string,
  groupId: string,
  templateId: string,
  sendTime: string,
): Promise<void> {
  await page.getByTestId('new-campaign').click();
  await page.getByTestId('campaign-name').fill(campaignName);
  await page
    .getByTestId('campaign-description')
    .fill('Playwright tracking and awareness happy path');
  await page.getByTestId('create-campaign').click();
  await expect(page.getByTestId('campaign-detail')).toContainText(campaignName);

  await page.getByTestId('campaign-template').selectOption(templateId);
  await page.getByTestId('wizard-next').click();

  const groupSelect = page.getByTestId('campaign-group');
  await expect(
    groupSelect.locator('option').filter({ hasText: groupName }),
  ).toHaveCount(1);
  await groupSelect.selectOption(groupId);
  await page.getByTestId('wizard-next').click();

  await page.getByTestId('campaign-send-time').fill(sendTime);
  await page.getByTestId('campaign-domain').fill('example.test');
  await page.getByTestId('wizard-next').click();
  await expect(page.getByTestId('review-scope')).toBeVisible();
  await page.getByTestId('wizard-next').click();
  await expect(page.getByTestId('authorization-status')).toBeVisible();

  await page.getByTestId('request-authorization').click();
  await expect(page.getByTestId('authorization-status')).toContainText(
    'Status: requested',
  );

  await switchDemoAdmin(page, 'admin2');
  await page.goto('/campaigns');
  const request = page
    .getByTestId('approvals-panel')
    .locator('li')
    .filter({ hasText: campaignName });
  await expect(request).toBeVisible();
  await request.getByRole('button', { name: 'Approve' }).click();
  await expect(page.getByText('Authorization approved.')).toBeVisible();

  await switchDemoAdmin(page, 'admin1');
  await page.goto('/campaigns');
  await page
    .getByTestId('campaign-list')
    .getByRole('button', { name: new RegExp(campaignName) })
    .click();
  await page.getByTestId('launch-campaign').click();
  const dialog = page.getByTestId('confirm-launch-dialog');
  await expect(dialog).toBeVisible();
  await page.getByTestId('confirm-launch').click();
  await expect(page.getByTestId('campaign-status')).toHaveText(/Scheduled|Running/);
}

async function waitForMessage(
  request: APIRequestContext,
  recipient: string,
): Promise<{ ID: string; To?: { Address?: string }[] }> {
  const deadline = Date.now() + 180_000;
  while (Date.now() < deadline) {
    const res = await request.get(`${MAILPIT_URL}/api/v1/messages?limit=200`);
    expect(res.ok()).toBeTruthy();
    const payload = (await res.json()) as {
      messages?: { ID: string; To?: { Address?: string }[] }[];
    };
    const match = (payload.messages ?? []).find((message) =>
      (message.To ?? []).some((to) => to.Address === recipient),
    );
    if (match) {
      return match;
    }
    await new Promise((resolve) => setTimeout(resolve, 2000));
  }
  throw new Error(`No Mailpit message arrived for ${recipient}`);
}

test('email link records a click, redirects to awareness, and passes axe light/dark', async ({
  page,
  request,
}: any) => {
  const stamp = Date.now();
  const campaignName = `Awareness campaign ${stamp}`;
  const groupName = `Awareness Group ${stamp}`;
  const recipient = `pw-awareness-${stamp}-0@example.test`;

  await page.goto('/campaigns');
  const groupId = await seedGroup(
    page,
    groupName,
    `pw-awareness-${stamp}`,
    5,
  );
  const templateId = await seedTemplate(
    page,
    `Awareness template ${stamp}`,
  );
  await page.reload();
  await createAndLaunch(
    page,
    campaignName,
    groupName,
    groupId,
    templateId,
    futureMinuteInput(90),
  );

  const message = await waitForMessage(request, recipient);
  const detail = await request.get(`${MAILPIT_URL}/api/v1/message/${message.ID}`);
  expect(detail.ok()).toBeTruthy();
  const body = (await detail.json()) as { HTML?: string; Text?: string };
  const html = body.HTML || body.Text || '';
  const linkMatch = html.match(/href="([^"]*\/t\/[^"]+)"/);
  expect(linkMatch).not.toBeNull();
  const trackingHref = linkMatch?.[1] ?? '';
  const token = trackingHref.split('/t/')[1];
  expect(token.length).toBeGreaterThanOrEqual(40);

  await page.setContent(html);
  await page.locator('a[href*="/t/"]').first().click();
  await page.waitForURL(new RegExp(`/learn/${token}$`));

  await expect(
    page.getByRole('heading', { name: 'This was a phishing simulation' }),
  ).toBeVisible();
  await expect(page.getByTestId('start-training')).toBeVisible();
  await expect(page.getByTestId('start-training')).toContainText(
    'Start 3-minute training',
  );
  await expect(page.getByTestId('report-link')).toBeVisible();
  await expect(page.getByText('Red flags in that email')).toBeVisible();

  await page.getByTestId('start-training').click();
  await expect(page).toHaveURL(/#training-tips$/);
  await expect(page.getByText('Three things to do next time')).toBeVisible();

  const light = await new AxeBuilder({ page }).analyze();
  const serious = light.violations.filter(
    (violation) => violation.impact === 'serious' || violation.impact === 'critical',
  );
  expect(serious).toEqual([]);

  await setDarkTheme(page);
  await page.waitForTimeout(500);
  const dark = await new AxeBuilder({ page }).analyze();
  const darkSerious = dark.violations.filter(
    (violation) => violation.impact === 'serious' || violation.impact === 'critical',
  );
  expect(darkSerious).toEqual([]);

  await page.evaluate(() => document.documentElement.classList.remove('dark'));

  await page.getByTestId('quiz-cta').click();
  await page.waitForURL(new RegExp(`/learn/${token}/quiz$`));
  await expect(
    page.getByRole('heading', { level: 1, name: 'Quick security check' }),
  ).toBeVisible();

  for (let question = 0; question < 5; question += 1) {
    await page.getByRole('radio').first().check();
    await expect(page.getByText('Why', { exact: true })).toBeVisible();
    const next = page.getByTestId('quiz-next');
    await expect(next).toBeEnabled();
    await next.click();
  }
  await expect(page.getByText('Training complete').first()).toBeVisible();
  await expect(
    page.getByRole('link', { name: 'Back to the awareness page' }).first(),
  ).toBeVisible();

  const quizLight = await new AxeBuilder({ page }).analyze();
  expect(
    quizLight.violations.filter(
      (violation) => violation.impact === 'serious' || violation.impact === 'critical',
    ),
  ).toEqual([]);
  await setDarkTheme(page);
  await page.waitForTimeout(500);
  const quizDark = await new AxeBuilder({ page }).analyze();
  expect(
    quizDark.violations.filter(
      (violation) => violation.impact === 'serious' || violation.impact === 'critical',
    ),
  ).toEqual([]);
  await page.evaluate(() => document.documentElement.classList.remove('dark'));

  await page.goto('/reports');
  await expect(page.getByRole('heading', { level: 1, name: 'Reports' })).toBeVisible();
  const campaignSelect = page.getByTestId('reports-campaign');
  await expect(
    campaignSelect.locator('option').filter({ hasText: campaignName }),
  ).toHaveCount(1);
  await campaignSelect.selectOption({ label: campaignName });
  await expect(page.getByTestId('report-funnel')).toBeVisible();
  await expect(page.getByTestId('report-groups')).toContainText(groupName);
  await expect(page.getByTestId('report-trend')).toBeVisible();

  const downloadPromise = page.waitForEvent('download');
  await page.getByTestId('reports-export').click();
  const download = await downloadPromise;
  expect(download.suggestedFilename()).toBe('campaign-report.csv');

  const reportsLight = await new AxeBuilder({ page }).analyze();
  expect(
    reportsLight.violations.filter(
      (violation) => violation.impact === 'serious' || violation.impact === 'critical',
    ),
  ).toEqual([]);
  await setDarkTheme(page);
  await page.waitForTimeout(500);
  const reportsDark = await new AxeBuilder({ page }).analyze();
  expect(
    reportsDark.violations.filter(
      (violation) => violation.impact === 'serious' || violation.impact === 'critical',
    ),
  ).toEqual([]);
  await page.evaluate(() => document.documentElement.classList.remove('dark'));

  await page.goto('/');
  await expect(page.getByTestId('dashboard-metric')).toHaveCount(4);
  const sentMetric = page
    .getByTestId('dashboard-metric')
    .filter({ hasText: 'Emails sent' });
  await expect(sentMetric).not.toContainText('—');
  const dashboardLight = await new AxeBuilder({ page }).analyze();
  expect(
    dashboardLight.violations.filter(
      (violation) => violation.impact === 'serious' || violation.impact === 'critical',
    ),
  ).toEqual([]);
  await setDarkTheme(page);
  await page.waitForTimeout(500);
  const dashboardDark = await new AxeBuilder({ page }).analyze();
  expect(
    dashboardDark.violations.filter(
      (violation) => violation.impact === 'serious' || violation.impact === 'critical',
    ),
  ).toEqual([]);
});
