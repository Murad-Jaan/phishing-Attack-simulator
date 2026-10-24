import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './tests',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: 'line',
  webServer: process.env.CI ? {
    command: 'npm run build && npm start',
    url: 'http://127.0.0.1:3000',
    reuseExistingServer: !process.env.CI,
    timeout: 300 * 1000,
  } : undefined,
  use: {
    baseURL: process.env.BASE_URL || (process.env.CI ? 'http://127.0.0.1:3000' : 'http://phishsim-web-prod:3000'),
    trace: 'on-first-retry',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
});
