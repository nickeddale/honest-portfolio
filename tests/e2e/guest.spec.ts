import { test, expect } from './fixtures';

test.describe('Guest Mode', () => {
  test.beforeEach(async ({ page, clearGuestData }) => {
    // Navigate to homepage
    await page.goto('/');

    // Wait for the page to load
    await page.waitForLoadState('networkidle');

    // Wait for the app to initialize and check that we're on the correct page
    await expect(page).toHaveTitle(/Honest Portfolio/);

    // Clear guest data
    await clearGuestData();

    // Wait a bit for the page to stabilize
    await page.waitForTimeout(500);
  });

  test('guest-can-add-stock-quick-mode', async ({ page }) => {
    // Verify we're on the Honest Portfolio page (not redirected to login)
    await expect(page).toHaveTitle(/Honest Portfolio/);

    // Wait for the form to be visible
    await expect(page.locator('#purchase-form-quick')).toBeVisible();

    // Verify we're in guest mode by checking for "Guest Mode" indicator or "Sign In" button
    const guestSection = page.locator('#guest-login-section');
    await expect(guestSection).toBeVisible({ timeout: 5000 });

    // Fill in the quick add form with a more recent date
    await page.fill('#ticker-quick', 'AAPL');
    await page.fill('#purchase-date-quick', '2024-11-15');
    await page.fill('#amount-quick', '1000');

    // Wait for any API calls to complete after form submission
    const responsePromise = page.waitForResponse(
      response => response.url().includes('/api/') && response.status() === 200,
      { timeout: 10000 }
    ).catch(() => null); // Don't fail if no API call is made (guest mode uses localStorage)

    // Submit the form
    await page.click('#submit-btn-quick');

    // Wait for the response or a short timeout for localStorage operations
    await Promise.race([
      responsePromise,
      page.waitForTimeout(1000)
    ]);

    // Wait for purchases section to become visible
    const purchasesSection = page.locator('#purchases-section');
    await expect(purchasesSection).toBeVisible({ timeout: 5000 });

    // Scroll to the purchases section
    await purchasesSection.scrollIntoViewIfNeeded();

    // Verify the purchase appears in the purchases list
    const purchasesList = page.locator('#purchases-list');
    await expect(purchasesList).toBeVisible();

    // Verify AAPL ticker is visible in the list
    await expect(purchasesList.locator('text=AAPL')).toBeVisible({ timeout: 5000 });

    // Verify purchase amount is visible (flexible matching for currency formatting)
    await expect(purchasesList).toContainText('$1,000');

    // Verify the date appears (may be formatted differently, just check for Nov)
    await expect(purchasesList).toContainText('Nov');
  });

  test('guest-can-view-portfolio-summary', async ({ page }) => {
    // Verify we're on the Honest Portfolio page
    await expect(page).toHaveTitle(/Honest Portfolio/);

    // Wait for the form to be visible
    await expect(page.locator('#purchase-form-quick')).toBeVisible();

    // Add a stock purchase using the form with a recent date
    await page.fill('#ticker-quick', 'AAPL');
    await page.fill('#purchase-date-quick', '2024-11-18');  // Monday to ensure valid trading day
    await page.fill('#amount-quick', '1000');

    // Wait for the guest API validation response
    const responsePromise = page.waitForResponse(
      response => response.url().includes('/api/guest/purchases/validate') && response.status() === 200,
      { timeout: 15000 }
    );

    await page.click('#submit-btn-quick');

    // Wait for the response
    await responsePromise;

    // Wait for summary section to become visible
    await expect(page.locator('#summary-section')).toBeVisible({ timeout: 5000 });

    // Verify "Total Invested" shows $1,000
    const totalInvested = page.locator('#total-invested');
    await expect(totalInvested).toBeVisible();
    await expect(totalInvested).toContainText('$1,000');

    // Verify "Current Value" is displayed (any value)
    const actualValue = page.locator('#actual-value');
    await expect(actualValue).toBeVisible();
    // Check that it contains a dollar sign and a number
    await expect(actualValue).toContainText('$');

    // Verify return percentage is displayed
    const actualReturn = page.locator('#actual-return');
    await expect(actualReturn).toBeVisible();
    // Check that it contains a percentage sign
    await expect(actualReturn).toContainText('%');
  });
});
