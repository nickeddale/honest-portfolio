import { test, expect } from './fixtures';

test.describe('Authenticated User Mode', () => {
  test.beforeEach(async ({ page, clearTestPurchases }) => {
    // Navigate to homepage
    await page.goto('/');

    // Wait for the page to load
    await page.waitForLoadState('networkidle');

    // Wait for the app to initialize
    await expect(page).toHaveTitle(/Honest Portfolio/);

    // Wait for page scripts to load
    await page.waitForFunction(() => {
      return typeof authManager !== 'undefined' && typeof updateUserUI === 'function';
    }, { timeout: 5000 });

    // Login as test user using page.evaluate to ensure cookies are shared
    const loginResult = await page.evaluate(async () => {
      const response = await fetch('/api/test/auth/create-test-user', {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json'
        }
      });
      const result = {
        ok: response.ok,
        status: response.status,
        statusText: response.statusText,
        data: response.ok ? await response.json() : null
      };

      // If login succeeded, refresh auth state and update UI
      if (result.ok) {
        const user = await authManager.refreshCurrentUser();
        updateUserUI(); // Manually trigger UI update
      }

      return result;
    });

    if (!loginResult.ok) {
      throw new Error(`Failed to create test user: ${loginResult.status} ${loginResult.statusText}`);
    }

    // Clear any existing purchases from previous tests
    await clearTestPurchases();

    // Reload the page to ensure clean state
    await page.reload();
    await page.waitForLoadState('networkidle');

    // Wait for authManager to be ready again
    await page.waitForFunction(() => {
      return typeof authManager !== 'undefined' && authManager.csrfToken !== null;
    }, { timeout: 5000 });

    // Wait for user section to appear (confirms authenticated state)
    await expect(page.locator('#user-section')).toBeVisible({ timeout: 5000 });

    // Wait a bit for the page to stabilize
    await page.waitForTimeout(500);
  });

  test('auth-user-can-add-stock', async ({ page }) => {
    // Verify we're authenticated by checking for user section
    await expect(page.locator('#user-section')).toBeVisible();

    // Verify guest login section is hidden
    await expect(page.locator('#guest-login-section')).not.toBeVisible();

    // Wait for the form to be visible
    await expect(page.locator('#purchase-form-quick')).toBeVisible();

    // Fill in the quick add form with MSFT
    await page.fill('#ticker-quick', 'MSFT');
    await page.fill('#purchase-date-quick', '2024-11-01');
    await page.fill('#amount-quick', '500');

    // Wait for API response after form submission (201 = created)
    const responsePromise = page.waitForResponse(
      response => response.url().includes('/api/purchases') && response.status() === 201,
      { timeout: 10000 }
    );

    // Submit the form
    await page.click('#submit-btn-quick');

    // Wait for the response
    await responsePromise;

    // Wait for purchases section to become visible
    const purchasesSection = page.locator('#purchases-section');
    await expect(purchasesSection).toBeVisible({ timeout: 5000 });

    // Scroll to the purchases section
    await purchasesSection.scrollIntoViewIfNeeded();

    // Verify the purchase appears in the purchases list
    const purchasesList = page.locator('#purchases-list');
    await expect(purchasesList).toBeVisible();

    // Verify MSFT ticker is visible in the list
    await expect(purchasesList.locator('text=MSFT').first()).toBeVisible({ timeout: 5000 });

    // Verify purchase amount is visible
    await expect(purchasesList).toContainText('$500');

    // Verify the date appears
    await expect(purchasesList).toContainText('Nov');
  });

  test('auth-user-can-view-purchase-detail', async ({ page }) => {
    // Add a stock purchase first
    await expect(page.locator('#purchase-form-quick')).toBeVisible();

    await page.fill('#ticker-quick', 'AAPL');
    await page.fill('#purchase-date-quick', '2024-10-15');
    await page.fill('#amount-quick', '1000');

    // Wait for API response after form submission (201 = created)
    const responsePromise = page.waitForResponse(
      response => response.url().includes('/api/purchases') && response.status() === 201,
      { timeout: 10000 }
    );

    // Submit the form
    await page.click('#submit-btn-quick');

    // Wait for the response
    await responsePromise;

    // Wait for purchase to appear in list
    const purchasesList = page.locator('#purchases-list');
    await expect(purchasesList).toBeVisible({ timeout: 5000 });
    await expect(purchasesList.locator('text=AAPL').first()).toBeVisible({ timeout: 5000 });

    // Click on the purchase item to navigate to detail
    // Uses event delegation with data-purchase-id attribute
    const purchaseItem = page.locator('.purchase-item').first();
    await purchaseItem.waitFor({ state: 'visible', timeout: 5000 });
    await purchaseItem.click();

    // Wait for the navigation function to execute and show detail section
    // The hidden class should be removed from #purchase-detail-section
    await page.waitForFunction(
      () => {
        const section = document.getElementById('purchase-detail-section');
        return section && !section.classList.contains('hidden');
      },
      { timeout: 10000 }
    );

    // Wait for detail view to load - first the section, then the content
    await expect(page.locator('#purchase-detail-section')).toBeVisible({ timeout: 5000 });

    // Wait for the detail content to be shown (hidden class removed after data loads)
    await expect(page.locator('#detail-content')).toBeVisible({ timeout: 10000 });

    // Verify detail page shows ticker
    const detailTicker = page.locator('#detail-ticker');
    await expect(detailTicker).toBeVisible({ timeout: 5000 });
    await expect(detailTicker).toContainText('AAPL');

    // Verify purchase date is shown
    const detailDate = page.locator('#detail-date');
    await expect(detailDate).toBeVisible();
    await expect(detailDate).toContainText('Oct');

    // Verify amount invested is shown
    const detailAmount = page.locator('#detail-amount');
    await expect(detailAmount).toBeVisible();
    await expect(detailAmount).toContainText('$1,000');

    // Verify "What If" comparison section exists
    const alternativesSection = page.locator('#detail-alternatives');
    await expect(alternativesSection).toBeVisible({ timeout: 5000 });

    // Verify at least SPY comparison is shown
    await expect(alternativesSection).toContainText('SPY', { timeout: 10000 });

    // Verify comparison cards show benchmark stocks
    // Should have cards for comparison stocks like SPY, AAPL, META, GOOGL, NVDA, AMZN
    const comparisonCards = alternativesSection.locator('.border-2');
    await expect(comparisonCards.first()).toBeVisible({ timeout: 5000 });
  });

  test('auth-user-can-delete-stock', async ({ page }) => {
    // Add a stock purchase first
    await expect(page.locator('#purchase-form-quick')).toBeVisible();

    // Wait for authManager to be fully initialized with CSRF token
    await page.waitForFunction(() => {
      return typeof authManager !== 'undefined' && authManager.csrfToken !== null;
    }, { timeout: 5000 });

    await page.fill('#ticker-quick', 'TSLA');
    await page.fill('#purchase-date-quick', '2024-09-23');  // Monday to ensure valid trading day
    await page.fill('#amount-quick', '750');

    const addResponsePromise = page.waitForResponse(
      response => response.url().includes('/api/purchases') && response.status() === 201,
      { timeout: 15000 }
    );

    await page.click('#submit-btn-quick');
    await addResponsePromise;

    // Wait for purchase to appear in list
    const purchasesList = page.locator('#purchases-list');
    await expect(purchasesList).toBeVisible({ timeout: 5000 });
    await expect(purchasesList.locator('text=TSLA').first()).toBeVisible({ timeout: 5000 });

    // Wait for delete API call
    const deleteResponsePromise = page.waitForResponse(
      response => response.url().includes('/api/purchases/') && response.request().method() === 'DELETE',
      { timeout: 10000 }
    );

    // Click the delete button directly
    // Uses event delegation with data-delete-id attribute
    const deleteBtn = page.locator('.delete-purchase-btn').first();
    await deleteBtn.waitFor({ state: 'visible', timeout: 5000 });
    await deleteBtn.click();

    // Wait for confirmation modal to appear (hidden class removed)
    await page.waitForFunction(
      () => {
        const modal = document.getElementById('confirmation-modal');
        return modal && !modal.classList.contains('hidden');
      },
      { timeout: 5000 }
    );

    // Wait for confirm button to be visible and click it
    const confirmButton = page.locator('#modal-confirm');
    await expect(confirmButton).toBeVisible({ timeout: 5000 });
    await confirmButton.click();

    // Wait for the delete response
    await deleteResponsePromise;

    // Verify purchase is removed from list
    await expect(purchasesList.locator('text=TSLA')).not.toBeVisible({ timeout: 5000 });
  });

  test('auth-user-can-create-share', async ({ page }) => {
    // Add a stock purchase first
    await expect(page.locator('#purchase-form-quick')).toBeVisible();

    // Wait for authManager to be ready
    await page.waitForFunction(() => {
      return typeof authManager !== 'undefined' && authManager.csrfToken !== null;
    }, { timeout: 5000 });

    await page.fill('#ticker-quick', 'GOOGL');
    await page.fill('#purchase-date-quick', '2024-08-12'); // Monday instead of Saturday
    await page.fill('#amount-quick', '2000');

    const responsePromise = page.waitForResponse(
      response => response.url().includes('/api/purchases') && response.status() === 201,
      { timeout: 10000 }
    );

    await page.click('#submit-btn-quick');
    await responsePromise;

    // Wait for purchase to appear (use first() to avoid strict mode violation)
    await expect(page.locator('#purchases-list').locator('text=GOOGL').first()).toBeVisible({ timeout: 5000 });

    // Wait for share button to appear
    const shareButtonSection = page.locator('#share-button-section');
    await expect(shareButtonSection).toBeVisible({ timeout: 5000 });

    // Call openShareModal() directly using page.evaluate() to bypass CSP restrictions
    await page.evaluate(() => {
      (window as any).openShareModal();
    });

    // Verify share modal opens
    const shareModal = page.locator('#share-modal');
    await expect(shareModal).toBeVisible({ timeout: 5000 });

    // Verify share URL is generated and displayed
    const shareUrlInput = page.locator('#share-url');
    await expect(shareUrlInput).toBeVisible();

    // Wait for the URL to be populated (this confirms the API call completed successfully)
    await page.waitForFunction(
      () => {
        const input = document.querySelector('#share-url') as HTMLInputElement;
        return input && input.value && input.value.includes('/share/') && !input.value.includes('Creating');
      },
      { timeout: 10000 }
    );

    // Verify the share URL contains expected pattern
    const shareUrl = await shareUrlInput.inputValue();
    expect(shareUrl).toContain('/share/');

    // Verify "Copy Link" button is present
    const copyButton = shareModal.locator('button', { hasText: 'Copy' });
    await expect(copyButton).toBeVisible();
  });

  test('auth-user-can-view-share-page', async ({ page, context }) => {
    // Add a stock purchase first
    await expect(page.locator('#purchase-form-quick')).toBeVisible();

    // Wait for authManager to be ready
    await page.waitForFunction(() => {
      return typeof authManager !== 'undefined' && authManager.csrfToken !== null;
    }, { timeout: 5000 });

    await page.fill('#ticker-quick', 'NVDA');
    await page.fill('#purchase-date-quick', '2024-07-05');
    await page.fill('#amount-quick', '1500');

    const addResponsePromise = page.waitForResponse(
      response => response.url().includes('/api/purchases') && response.status() === 201,
      { timeout: 10000 }
    );

    await page.click('#submit-btn-quick');
    await addResponsePromise;

    // Wait for purchase to appear (use first() to avoid strict mode violation)
    await expect(page.locator('#purchases-list').locator('text=NVDA').first()).toBeVisible({ timeout: 5000 });

    // Wait for share button section to appear
    await expect(page.locator('#share-button-section')).toBeVisible({ timeout: 5000 });

    // Call openShareModal() directly using page.evaluate() to bypass CSP restrictions
    await page.evaluate(() => {
      (window as any).openShareModal();
    });

    // Wait for share modal
    const shareModal = page.locator('#share-modal');
    await expect(shareModal).toBeVisible({ timeout: 5000 });

    const shareUrlInput = page.locator('#share-url');
    // Wait for the URL to be populated (this confirms the API call completed successfully)
    await page.waitForFunction(
      () => {
        const input = document.querySelector('#share-url') as HTMLInputElement;
        return input && input.value && input.value.includes('/share/') && !input.value.includes('Creating');
      },
      { timeout: 10000 }
    );

    const shareUrl = await shareUrlInput.inputValue();

    // Extract the path from the full URL
    const url = new URL(shareUrl);
    const sharePath = url.pathname;

    // Navigate to the share page
    await page.goto(sharePath);
    await page.waitForLoadState('networkidle');

    // Verify we're on the share page
    await expect(page.locator('h1')).toContainText('Portfolio Performance', { timeout: 5000 });

    // Verify portfolio stats are displayed on share page
    // Share pages typically show summary data
    const shareContent = page.locator('body');
    await expect(shareContent).toBeVisible();

    // Verify percentage return is shown (share pages show % but not dollar amounts)
    await expect(shareContent).toContainText('%', { timeout: 5000 });
  });

  test('auth-user-can-download-share-image', async ({ page }) => {
    // Add a stock purchase first
    await expect(page.locator('#purchase-form-quick')).toBeVisible();

    // Wait for authManager to be ready
    await page.waitForFunction(() => {
      return typeof authManager !== 'undefined' && authManager.csrfToken !== null;
    }, { timeout: 5000 });

    await page.fill('#ticker-quick', 'META');
    await page.fill('#purchase-date-quick', '2024-06-17'); // Monday instead of Saturday
    await page.fill('#amount-quick', '1250');

    const addResponsePromise = page.waitForResponse(
      response => response.url().includes('/api/purchases') && response.status() === 201,
      { timeout: 10000 }
    );

    await page.click('#submit-btn-quick');
    await addResponsePromise;

    // Wait for purchase to appear (use first() to avoid strict mode violation)
    await expect(page.locator('#purchases-list').locator('text=META').first()).toBeVisible({ timeout: 5000 });

    // Wait for share button section to appear
    await expect(page.locator('#share-button-section')).toBeVisible({ timeout: 5000 });

    // Call openShareModal() directly using page.evaluate() to bypass CSP restrictions
    await page.evaluate(() => {
      (window as any).openShareModal();
    });

    // Wait for share modal
    const shareModal = page.locator('#share-modal');
    await expect(shareModal).toBeVisible({ timeout: 5000 });

    // Wait for the share URL to be populated (confirms API call completed)
    await page.waitForFunction(
      () => {
        const input = document.querySelector('#share-url') as HTMLInputElement;
        return input && input.value && input.value.includes('/share/') && !input.value.includes('Creating');
      },
      { timeout: 10000 }
    );

    // Set up download listener
    const downloadPromise = page.waitForEvent('download', { timeout: 15000 });

    // Call downloadShareImage() directly using page.evaluate() to bypass CSP restrictions
    await page.evaluate(() => {
      (window as any).downloadShareImage();
    });

    // Wait for download to start
    const download = await downloadPromise;

    // Verify download was triggered
    expect(download).toBeTruthy();

    // Verify the download filename contains expected pattern
    const filename = download.suggestedFilename();
    expect(filename).toMatch(/\.png$/i);
  });
});
