import { defineConfig, devices } from '@playwright/test';

/**
 * Playwright configuration for Flask app end-to-end testing
 * See https://playwright.dev/docs/test-configuration
 */
export default defineConfig({
  testDir: './tests/e2e',

  /* Maximum time one test can run for */
  timeout: 30 * 1000,

  /* Run tests in files in parallel */
  fullyParallel: false,

  /* Fail the build on CI if you accidentally left test.only in the source code */
  forbidOnly: !!process.env.CI,

  /* Retry on CI only */
  retries: process.env.CI ? 2 : 0,

  /* Opt out of parallel tests on CI */
  workers: 1,

  /* Reporter to use */
  reporter: 'html',

  /* Shared settings for all the projects below */
  use: {
    /* Base URL to use in actions like `await page.goto('/')` */
    baseURL: 'http://localhost:5000',

    /* Collect trace when retrying the failed test */
    trace: 'on-first-retry',

    /* Screenshot on failure */
    screenshot: 'only-on-failure',
  },

  /* Configure projects for browsers - using only Chromium for speed */
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],

  /* Run Flask development server before starting the tests */
  webServer: {
    command: 'source venv/bin/activate && FLASK_USE_RELOADER=0 python run.py',
    port: 5000,
    reuseExistingServer: !process.env.CI,
    env: {
      ENABLE_TEST_AUTH: 'true',
      FLASK_USE_RELOADER: '0',
    },
  },
});
