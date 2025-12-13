import { test, expect, loginAsTestUser, clearGuestData, addGuestPurchase } from './fixtures';

test.describe('Authentication', () => {
  test.beforeEach(async ({ page, clearGuestData }) => {
    // Navigate to homepage
    await page.goto('/');

    // Wait for the page to load
    await page.waitForLoadState('networkidle');

    // Wait for the app to initialize
    await expect(page).toHaveTitle(/Honest Portfolio/);

    // Clear guest data to start fresh
    await clearGuestData();

    // Wait for the page to stabilize
    await page.waitForTimeout(500);
  });

  test('user-can-login-via-test-auth', async ({ page }) => {
    // Verify we're initially in guest mode
    const guestSection = page.locator('#guest-login-section');
    await expect(guestSection).toBeVisible({ timeout: 5000 });

    // Verify the "Sign In" button is visible
    const signInButton = guestSection.locator('button:has-text("Sign In")');
    await expect(signInButton).toBeVisible();

    // Verify user section is hidden
    const userSection = page.locator('#user-section');
    await expect(userSection).toBeHidden();

    // Login as test user
    const userInfo = await loginAsTestUser(page);

    // Verify the login was successful
    expect(userInfo).toBeDefined();
    expect(userInfo.user).toBeDefined();
    expect(userInfo.user.name).toBe('Test User');

    // Reload the page to trigger the auth state check
    await page.reload();
    await page.waitForLoadState('networkidle');

    // Wait for the user section to become visible
    await expect(userSection).toBeVisible({ timeout: 5000 });

    // Verify guest section is now hidden
    await expect(guestSection).toBeHidden();

    // Verify the user name is displayed
    const userName = page.locator('#user-name');
    await expect(userName).toBeVisible();
    await expect(userName).toContainText('Test User');

    // Verify the "Sign In" button is no longer visible
    await expect(signInButton).toBeHidden();

    // Verify logout button is visible
    const logoutButton = page.locator('#logout-btn');
    await expect(logoutButton).toBeVisible();
  });

  test('guest-data-migrates-on-login', async ({ page }) => {
    // Verify we're in guest mode
    const guestSection = page.locator('#guest-login-section');
    await expect(guestSection).toBeVisible({ timeout: 5000 });

    // Wait for form to be visible
    await expect(page.locator('#purchase-form-quick')).toBeVisible();

    // Add a guest purchase via the UI form
    await page.fill('#ticker-quick', 'AAPL');

    // Use a recent date for the purchase
    const recentDate = new Date();
    recentDate.setDate(recentDate.getDate() - 30); // 30 days ago
    const dateString = recentDate.toISOString().split('T')[0];
    await page.fill('#purchase-date-quick', dateString);

    await page.fill('#amount-quick', '1000');

    // Wait for any API calls after submission (or localStorage update)
    const responsePromise = page.waitForResponse(
      response => response.url().includes('/api/') && response.status() === 200,
      { timeout: 10000 }
    ).catch(() => null); // Don't fail if no API call is made (guest mode uses localStorage)

    // Submit the form
    await page.click('#submit-btn-quick');

    // Wait for the response or localStorage update
    await Promise.race([
      responsePromise,
      page.waitForTimeout(1000)
    ]);

    // Wait for purchases section to become visible
    const purchasesSection = page.locator('#purchases-section');
    await expect(purchasesSection).toBeVisible({ timeout: 5000 });

    // Scroll to the purchases section
    await purchasesSection.scrollIntoViewIfNeeded();

    // Verify the purchase appears in the guest purchases list
    const purchasesList = page.locator('#purchases-list');
    await expect(purchasesList).toBeVisible();

    // Verify AAPL ticker is visible in the list
    await expect(purchasesList.locator('text=AAPL')).toBeVisible({ timeout: 5000 });

    // Verify purchase amount is visible
    await expect(purchasesList).toContainText('$1,000');

    // Verify guest localStorage contains the purchase
    const guestPurchasesBeforeLogin = await page.evaluate(() => {
      return localStorage.getItem('honest_portfolio_guest_purchases');
    });
    expect(guestPurchasesBeforeLogin).toBeTruthy();
    expect(guestPurchasesBeforeLogin).toContain('AAPL');

    // Login as test user
    const userInfo = await loginAsTestUser(page);
    expect(userInfo).toBeDefined();
    expect(userInfo.user).toBeDefined();
    expect(userInfo.user.name).toBe('Test User');

    // Reload the page to trigger migration
    await page.reload();
    await page.waitForLoadState('networkidle');

    // Wait for user section to be visible (confirming we're logged in)
    const userSection = page.locator('#user-section');
    await expect(userSection).toBeVisible({ timeout: 5000 });

    // Verify the purchase was migrated and is still visible
    await expect(purchasesSection).toBeVisible({ timeout: 5000 });
    await purchasesSection.scrollIntoViewIfNeeded();

    // Verify AAPL ticker is still visible in the purchases list
    await expect(purchasesList.locator('text=AAPL').first()).toBeVisible({ timeout: 5000 });

    // Verify purchase amount is still visible
    await expect(purchasesList).toContainText('$1,000');

    // Verify localStorage guest purchases are cleared after migration
    const guestPurchasesAfterLogin = await page.evaluate(() => {
      return localStorage.getItem('honest_portfolio_guest_purchases');
    });

    // The guest purchases should be cleared (either null or empty array)
    if (guestPurchasesAfterLogin !== null) {
      const parsedPurchases = JSON.parse(guestPurchasesAfterLogin);
      expect(Array.isArray(parsedPurchases)).toBe(true);
      expect(parsedPurchases.length).toBe(0);
    }
  });
});
