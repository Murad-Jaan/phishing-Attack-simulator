import { defineConfig, devices } from '@playwright/test';

// baseURL is environment-driven:
//   - docker dev-stack runs:  BASE_URL default http://phishsim-web:3000 (compose service)
//   - CI / local host runs:   BASE_URL=http://127.0.0.1:3000 (webServer `npm start`)
// The API address the web server itself talks to comes from API_INTERNAL_URL
// (default http://127.0.0.1:8000), set in the environment before `npx playwright test`.

export default defineConfig({
  testDir: './tests',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: 'line',
  webServer: process.env.CI
    ? {
        command: 'npm run build && npm start',
        url: 'http://127.0.0.1:3000',
        reuseExistingServer: !process.env.CI,
        timeout: 300 * 1000,
      }
    : {
        command: 'npm run build && npm start -- -p 3001',
        url: 'http://127.0.0.1:3001/login',
        reuseExistingServer: true,
        timeout: 300 * 1000,
        env: {
          NODE_ENV: 'production',
          APP_ENV: 'production',
          API_INTERNAL_URL: process.env.API_INTERNAL_URL ?? 'http://api:8000',
        },
      },
  use: {
    baseURL: process.env.BASE_URL || (process.env.CI ? 'http://127.0.0.1:3000' : 'http://phishsim-web:3000'),
    trace: 'on-first-retry',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
});
