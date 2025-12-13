import { test as base, Page } from '@playwright/test';

/**
 * Helper function to create and login a test user
 * Requires ENABLE_TEST_AUTH=true environment variable
 *
 * @param page - Playwright page object
 * @returns User info object
 */
export async function loginAsTestUser(page: Page) {
  // Wait for page scripts to load
  await page.waitForFunction(() => {
    return typeof authManager !== 'undefined' && typeof updateUserUI === 'function';
  }, { timeout: 5000 });

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
      await authManager.refreshCurrentUser();
      updateUserUI(); // Manually trigger UI update
    }

    return result;
  });

  if (!loginResult.ok) {
    throw new Error(`Failed to create test user: ${loginResult.status} ${loginResult.statusText}`);
  }

  return loginResult.data;
}

/**
 * Helper function to clear all purchases for the authenticated test user
 *
 * @param page - Playwright page object
 */
export async function clearTestPurchases(page: Page) {
  const result = await page.evaluate(async () => {
    const response = await fetch('/api/test/auth/clear-purchases', {
      method: 'POST',
      credentials: 'include',
      headers: {
        'Content-Type': 'application/json'
      }
    });
    return {
      ok: response.ok,
      status: response.status,
      data: response.ok ? await response.json() : null
    };
  });

  if (!result.ok) {
    throw new Error(`Failed to clear test purchases: ${result.status}`);
  }

  return result.data;
}

/**
 * Helper function to clear guest purchase data from localStorage
 *
 * @param page - Playwright page object
 */
export async function clearGuestData(page: Page) {
  await page.evaluate(() => {
    localStorage.removeItem('honest_portfolio_guest_purchases');
  });
}

/**
 * Helper function to add a purchase to guest localStorage
 *
 * @param page - Playwright page object
 * @param purchase - Purchase data object
 */
export async function addGuestPurchase(
  page: Page,
  purchase: { ticker: string; date: string; amount: number }
) {
  await page.evaluate((purchaseData) => {
    // Get existing purchases or initialize empty array
    const existingPurchases = JSON.parse(
      localStorage.getItem('honest_portfolio_guest_purchases') || '[]'
    );

    // Add new purchase with a temporary ID
    const newPurchase = {
      id: `guest_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      ...purchaseData,
    };

    existingPurchases.push(newPurchase);

    // Save back to localStorage
    localStorage.setItem(
      'honest_portfolio_guest_purchases',
      JSON.stringify(existingPurchases)
    );
  }, purchase);
}

/**
 * Custom test fixture that extends the base Playwright test
 * Provides helper functions for authentication and guest data management
 */
export const test = base.extend<{
  loginAsTestUser: () => Promise<any>;
  clearTestPurchases: () => Promise<any>;
  clearGuestData: () => Promise<void>;
  addGuestPurchase: (purchase: { ticker: string; date: string; amount: number }) => Promise<void>;
}>({
  loginAsTestUser: async ({ page }, use) => {
    await use(() => loginAsTestUser(page));
  },

  clearTestPurchases: async ({ page }, use) => {
    await use(() => clearTestPurchases(page));
  },

  clearGuestData: async ({ page }, use) => {
    await use(() => clearGuestData(page));
  },

  addGuestPurchase: async ({ page }, use) => {
    await use((purchase) => addGuestPurchase(page, purchase));
  },
});

export { expect } from '@playwright/test';
