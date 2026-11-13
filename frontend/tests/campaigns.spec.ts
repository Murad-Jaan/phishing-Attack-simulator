import { test, expect, type Page } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

const ADMIN_1 = 'demo-admin-1@example.test';
const ADMIN_2 = 'demo-admin-2@example.test';

function passwordFor(email: string): string {
  const name = email === ADMIN_1 ? 'DEMO_ADMIN_1_PASSWORD' : 'DEMO_ADMIN_2_PASSWORD';
  const password = process.env[name] ?? '';
  expect(
    password,
    `${name} must be provided at run time and \`make seed\` must have run on the dev DB`,
  ).toMatch(/^\S{12,}$/);
  return password;
}

async function loginAs(page: Page, email: string): Promise<void> {
  await page.goto('/login');
  await page.getByTestId('login-email').fill(email);
  await page.getByTestId('login-password').fill(passwordFor(email));
  await page.getByTestId('login-submit').click();
  await page.waitForURL('/');
}

async function signOut(page: Page): Promise<void> {
  await page.getByTestId('sign-out').click();
  await page.waitForURL('/login');
}

async function seedGroup(page: Page, name: string, members: number): Promise<string> {
  return page.evaluate(
    async ({ name, members }) => {
      async function csrf(): Promise<string> {
        const res = await fetch('/api/v1/auth/csrf', {
          cache: 'no-store',
          credentials: 'same-origin',
        });
        const data = (await res.json()) as { csrf_token: string };
        return data.csrf_token;
      }
      const headers = (token: string) => ({
        'Content-Type': 'application/json',
        'X-CSRF-Token': token,
      });
      const token = await csrf();
      const created = await fetch('/api/v1/groups', {
        method: 'POST',
        credentials: 'same-origin',
        headers: headers(token),
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
          headers: headers(token),
          body: JSON.stringify({
            email: `pw-m5-${name.toLowerCase().replace(/[^a-z0-9]+/g, '-')}-${index}@example.test`,
            display_name: `M5 Member ${index}`,
          }),
        });
        if (!member.ok) {
          throw new Error(`member create failed: ${member.status}`);
        }
      }
      return group.group.id;
    },
    { name, members },
  );
}

function futureLocalInput(days: number): string {
  return new Date(Date.now() + days * 24 * 60 * 60 * 1000).toISOString().slice(0, 16);
}

async function createDraft(page: Page, name: string): Promise<void> {
  await page.getByTestId('new-campaign').click();
  await page.getByTestId('campaign-name').fill(name);
  await page.getByTestId('campaign-description').fill('Playwright M5 happy path');
  await page.getByTestId('create-campaign').click();
  await expect(page.getByTestId('campaign-detail')).toContainText(name);
}

async function fillWizard(page: Page, groupId: string): Promise<void> {
  await page.getByTestId('campaign-template').selectOption({ index: 1 });
  await page.getByTestId('wizard-next').click();

  await page.getByTestId('campaign-group').selectOption(groupId);
  await page.getByTestId('wizard-next').click();

  await page.getByTestId('campaign-send-time').fill(futureLocalInput(3));
  await page.getByTestId('campaign-domain').fill('example.test');
  await page.getByTestId('wizard-next').click();

  await expect(page.getByTestId('review-scope')).toBeVisible();
  await page.getByTestId('wizard-next').click();
  await expect(page.getByTestId('authorization-status')).toBeVisible();
}

function seriousViolations(violations: { impact?: string | null }[]) {
  return violations.filter((v) => v.impact === 'serious' || v.impact === 'critical');
}

test.describe('Campaigns', () => {
  test('happy path: draft, test send, two-admin approval and impact confirmation', async ({
    page,
  }: any) => {
    const stamp = Date.now();
    const campaignName = `M5 campaign ${stamp}`;
    const groupName = `M5 Group ${stamp}`;

    await loginAs(page, ADMIN_1);
    const groupId = await seedGroup(page, groupName, 5);
    await page.goto('/campaigns');
    await createDraft(page, campaignName);
    await fillWizard(page, groupId);

    await page.getByTestId('test-send-recipient').fill('sandbox@example.test');
    await page.getByTestId('test-send').click();
    await expect(page.getByTestId('test-send-result')).toContainText(
      'sandbox@example.test',
    );

    await page.getByTestId('request-authorization').click();
    await expect(page.getByTestId('authorization-status')).toContainText(
      'Status: requested',
    );
    await expect(page.getByText('Authorization requested.')).toBeVisible();

    await signOut(page);
    await loginAs(page, ADMIN_2);
    await page.goto('/campaigns');

    const request = page
      .getByTestId('approvals-panel')
      .locator('li')
      .filter({ hasText: campaignName });
    await expect(request).toBeVisible();
    await request.getByRole('button', { name: 'Approve' }).click();
    await expect(page.getByText('Authorization approved.')).toBeVisible();

    await signOut(page);
    await loginAs(page, ADMIN_1);
    await page.goto('/campaigns');
    await page
      .getByTestId('campaign-list')
      .getByRole('button', { name: new RegExp(campaignName) })
      .click();
    await expect(page.getByTestId('campaign-status')).toHaveText('Approved');

    await page.getByTestId('launch-campaign').click();
    const dialog = page.getByTestId('confirm-launch-dialog');
    await expect(dialog).toBeVisible();
    await expect(dialog).toContainText('Send to 5 people on');
    await expect(dialog).toContainText(groupName);
    await page.getByTestId('confirm-launch').click();
    await expect(page.getByTestId('campaign-status')).toHaveText(/Scheduled|Running/);
    await expect(page.getByText('Campaign launched.')).toBeVisible();
  });

  test('campaign creator has no serious or critical axe issues in light mode', async ({
    page,
  }: any) => {
    const stamp = Date.now();
    await loginAs(page, ADMIN_1);
    await page.goto('/campaigns');
    await createDraft(page, `M5 axe light ${stamp}`);
    const results = await new AxeBuilder({ page }).analyze();
    expect(seriousViolations(results.violations)).toEqual([]);
  });

  test('campaign creator has no serious or critical axe issues in dark mode', async ({
    page,
  }: any) => {
    const stamp = Date.now();
    await loginAs(page, ADMIN_1);
    await page.goto('/campaigns');
    await createDraft(page, `M5 axe dark ${stamp}`);
    await page.evaluate(() => document.documentElement.classList.add('dark'));
    const results = await new AxeBuilder({ page }).analyze();
    expect(seriousViolations(results.violations)).toEqual([]);
  });
});
