import { test, expect } from './fixtures';
import path from 'path';
import fs from 'fs';

test.describe('PDF Upload Feature', () => {
  test('pdf-upload-tab-displays-correctly', async ({ page }) => {
    // Navigate to homepage
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    // Verify PDF Upload tab exists
    const pdfUploadTab = page.locator('#tab-pdf-upload');
    await expect(pdfUploadTab).toBeVisible();
    await expect(pdfUploadTab).toContainText('PDF Upload');

    // Click the PDF Upload tab
    await pdfUploadTab.click();

    // Verify the PDF Upload panel becomes visible
    const pdfUploadPanel = page.locator('#panel-pdf-upload');
    await expect(pdfUploadPanel).toBeVisible();

    // Verify drop zone is displayed
    const dropZone = page.locator('#pdf-drop-zone');
    await expect(dropZone).toBeVisible();

    // Verify file input exists (even though it's hidden)
    const fileInput = page.locator('#pdf-file-input');
    await expect(fileInput).toBeAttached();

    // Verify upload text is present
    await expect(pdfUploadPanel).toContainText('Click to upload PDF');
    await expect(pdfUploadPanel).toContainText('or drag and drop');
    await expect(pdfUploadPanel).toContainText('Supports brokerage statements');
  });

  test.describe('Authenticated PDF Upload Tests', () => {
    test.beforeEach(async ({ page, clearTestPurchases }) => {
      // Navigate to homepage
      await page.goto('/');
      await page.waitForLoadState('networkidle');

      // Wait for the app to initialize
      await expect(page).toHaveTitle(/Honest Portfolio/);

      // Wait for page scripts to load
      await page.waitForFunction(() => {
        return typeof authManager !== 'undefined' && typeof updateUserUI === 'function';
      }, { timeout: 5000 });

      // Login as test user
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

        if (result.ok) {
          const user = await authManager.refreshCurrentUser();
          updateUserUI();
        }

        return result;
      });

      if (!loginResult.ok) {
        throw new Error(`Failed to create test user: ${loginResult.status} ${loginResult.statusText}`);
      }

      // Clear any existing purchases
      await clearTestPurchases();

      // Reload the page to ensure clean state
      await page.reload();
      await page.waitForLoadState('networkidle');

      // Wait for authManager to be ready again
      await page.waitForFunction(() => {
        return typeof authManager !== 'undefined' && authManager.csrfToken !== null;
      }, { timeout: 5000 });

      // Wait for user section to appear
      await expect(page.locator('#user-section')).toBeVisible({ timeout: 5000 });

      // Navigate to PDF Upload tab
      const pdfUploadTab = page.locator('#tab-pdf-upload');
      await pdfUploadTab.click();
      await expect(page.locator('#panel-pdf-upload')).toBeVisible();
    });

    test('pdf-upload-rejects-non-pdf-file', async ({ page }) => {
      // Create a temporary non-PDF file
      const tempDir = path.join(__dirname, '../../test-results/temp');
      if (!fs.existsSync(tempDir)) {
        fs.mkdirSync(tempDir, { recursive: true });
      }
      const txtFilePath = path.join(tempDir, 'test-file.txt');
      fs.writeFileSync(txtFilePath, 'This is not a PDF file');

      // Set up file chooser handler
      const fileInput = page.locator('#pdf-file-input');

      // Upload the non-PDF file
      await fileInput.setInputFiles(txtFilePath);

      // Wait for error status to appear
      const statusDiv = page.locator('#pdf-upload-status');
      await expect(statusDiv).toBeVisible({ timeout: 3000 });

      // Verify error message is displayed
      await expect(statusDiv).toContainText('PDF');

      // Clean up
      fs.unlinkSync(txtFilePath);
    });

    test('pdf-upload-shows-loading-state', async ({ page }) => {
      // Create a temporary PDF file for testing
      const tempDir = path.join(__dirname, '../../test-results/temp');
      if (!fs.existsSync(tempDir)) {
        fs.mkdirSync(tempDir, { recursive: true });
      }
      const pdfFilePath = path.join(tempDir, 'test.pdf');

      // Create a minimal valid PDF file
      const minimalPdf = `%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R >>
endobj
4 0 obj
<< /Length 44 >>
stream
BT
/F1 12 Tf
100 700 Td
(Test PDF) Tj
ET
endstream
endobj
xref
0 5
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
0000000214 00000 n
trailer
<< /Size 5 /Root 1 0 R >>
startxref
308
%%EOF`;
      fs.writeFileSync(pdfFilePath, minimalPdf);

      // Mock the API response to simulate processing delay
      await page.route('**/api/uploads/pdf/extract', async route => {
        // Delay to allow loading state to be visible
        await new Promise(resolve => setTimeout(resolve, 1000));

        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            trades: [],
            notes: ['Test processing']
          })
        });
      });

      // Set up file input
      const fileInput = page.locator('#pdf-file-input');

      // Upload the PDF file
      await fileInput.setInputFiles(pdfFilePath);

      // Verify loading state appears
      const statusDiv = page.locator('#pdf-upload-status');
      await expect(statusDiv).toBeVisible({ timeout: 2000 });

      // Check for loading indicator (spinner SVG or loading text)
      const isLoading = await statusDiv.locator('svg.animate-spin').isVisible()
        .catch(() => false);

      if (!isLoading) {
        // Alternative: check for loading text
        await expect(statusDiv).toContainText('Extracting', { timeout: 1000 });
      }

      // Clean up
      fs.unlinkSync(pdfFilePath);
    });

    test('pdf-upload-shows-confirmation-modal', async ({ page }) => {
      // Create a temporary PDF file
      const tempDir = path.join(__dirname, '../../test-results/temp');
      if (!fs.existsSync(tempDir)) {
        fs.mkdirSync(tempDir, { recursive: true });
      }
      const pdfFilePath = path.join(tempDir, 'test.pdf');

      // Create a minimal valid PDF
      const minimalPdf = `%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>
endobj
xref
0 4
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
trailer
<< /Size 4 /Root 1 0 R >>
startxref
195
%%EOF`;
      fs.writeFileSync(pdfFilePath, minimalPdf);

      // Mock the API response with extracted trades
      await page.route('**/api/uploads/pdf/extract', async route => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            trades: [
              {
                id: 'trade-1',
                ticker: 'AAPL',
                purchase_date: '2024-11-01',
                quantity: 10,
                price_per_share: 150.00,
                total_amount: 1500.00,
                validation: {
                  valid: true,
                  errors: []
                }
              },
              {
                id: 'trade-2',
                ticker: 'INVALID',
                purchase_date: '2024-11-02',
                quantity: 5,
                price_per_share: 100.00,
                total_amount: 500.00,
                validation: {
                  valid: false,
                  errors: ['Invalid ticker symbol']
                }
              }
            ],
            notes: ['Successfully extracted 2 trades']
          })
        });
      });

      // Upload the PDF file
      const fileInput = page.locator('#pdf-file-input');
      await fileInput.setInputFiles(pdfFilePath);

      // Wait for confirmation modal to appear
      const modal = page.locator('#pdf-confirm-modal');
      await expect(modal).toBeVisible({ timeout: 5000 });

      // Verify modal title
      await expect(modal).toContainText('Review Extracted Trades');

      // Verify trades table is visible
      const tradesTable = modal.locator('table');
      await expect(tradesTable).toBeVisible();

      // Verify table headers
      await expect(tradesTable).toContainText('Ticker');
      await expect(tradesTable).toContainText('Date');
      await expect(tradesTable).toContainText('Shares');
      await expect(tradesTable).toContainText('Price');
      await expect(tradesTable).toContainText('Total');
      await expect(tradesTable).toContainText('Status');

      // Verify trades are displayed in the table
      const tbody = modal.locator('#pdf-trades-tbody');

      // Check that we have the right number of rows
      const rows = tbody.locator('tr');
      await expect(rows).toHaveCount(2);

      // Verify AAPL ticker is in an input field
      const aaplInput = tbody.locator('input[data-field="ticker"]').first();
      await expect(aaplInput).toHaveValue('AAPL');

      // Verify INVALID ticker is in an input field
      const invalidInput = tbody.locator('input[data-field="ticker"]').nth(1);
      await expect(invalidInput).toHaveValue('INVALID');

      // Verify valid trade shows checkmark (✓) - using HTML entity &#10003;
      const firstRow = rows.first();
      await expect(firstRow).toContainText('✓');

      // Verify invalid trade shows X (❌) - using HTML entity &#10060;
      const secondRow = rows.nth(1);
      await expect(secondRow).toContainText('❌');

      // Verify action buttons are present
      const cancelBtn = modal.locator('#pdf-cancel-btn');
      const saveBtn = modal.locator('#pdf-save-btn');
      await expect(cancelBtn).toBeVisible();
      await expect(saveBtn).toBeVisible();
      await expect(saveBtn).toContainText('Save Selected Trades');

      // Verify trade count is displayed
      await expect(modal).toContainText('of');
      await expect(modal).toContainText('trades selected');

      // Clean up
      fs.unlinkSync(pdfFilePath);
    });

    test('pdf-upload-can-cancel-modal', async ({ page }) => {
      // Create a temporary PDF file
      const tempDir = path.join(__dirname, '../../test-results/temp');
      if (!fs.existsSync(tempDir)) {
        fs.mkdirSync(tempDir, { recursive: true });
      }
      const pdfFilePath = path.join(tempDir, 'test.pdf');

      // Create a minimal valid PDF
      const minimalPdf = `%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>
endobj
xref
0 4
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
trailer
<< /Size 4 /Root 1 0 R >>
startxref
195
%%EOF`;
      fs.writeFileSync(pdfFilePath, minimalPdf);

      // Mock the API response
      await page.route('**/api/uploads/pdf/extract', async route => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            trades: [
              {
                id: 'trade-1',
                ticker: 'MSFT',
                purchase_date: '2024-11-01',
                quantity: 10,
                price_per_share: 150.00,
                total_amount: 1500.00,
                validation: {
                  valid: true,
                  errors: []
                }
              }
            ],
            notes: []
          })
        });
      });

      // Upload the PDF file
      const fileInput = page.locator('#pdf-file-input');
      await fileInput.setInputFiles(pdfFilePath);

      // Wait for modal to appear
      const modal = page.locator('#pdf-confirm-modal');
      await expect(modal).toBeVisible({ timeout: 5000 });

      // Click cancel button
      const cancelBtn = modal.locator('#pdf-cancel-btn');
      await cancelBtn.click();

      // Verify modal is closed (hidden)
      await expect(modal).not.toBeVisible({ timeout: 3000 });

      // Clean up
      fs.unlinkSync(pdfFilePath);
    });
  });

  test('pdf-upload-requires-auth', async ({ page }) => {
    // Navigate to homepage WITHOUT logging in
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    // Wait for the app to initialize
    await expect(page).toHaveTitle(/Honest Portfolio/);

    // Navigate to PDF Upload tab
    const pdfUploadTab = page.locator('#tab-pdf-upload');
    await pdfUploadTab.click();
    await expect(page.locator('#panel-pdf-upload')).toBeVisible();

    // Create a temporary PDF file
    const tempDir = path.join(__dirname, '../../test-results/temp');
    if (!fs.existsSync(tempDir)) {
      fs.mkdirSync(tempDir, { recursive: true });
    }
    const pdfFilePath = path.join(tempDir, 'test.pdf');

    // Create a minimal valid PDF
    const minimalPdf = `%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>
endobj
xref
0 4
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
trailer
<< /Size 4 /Root 1 0 R >>
startxref
195
%%EOF`;
    fs.writeFileSync(pdfFilePath, minimalPdf);

    // Wait for page to be ready
    await page.waitForFunction(() => {
      return typeof authManager !== 'undefined';
    }, { timeout: 5000 });

    // Try to upload without authentication
    const fileInput = page.locator('#pdf-file-input');

    // Set up response handler to verify 401 or appropriate auth error
    let responseStatus = 0;
    page.on('response', response => {
      if (response.url().includes('/api/uploads/pdf/extract')) {
        responseStatus = response.status();
      }
    });

    await fileInput.setInputFiles(pdfFilePath);

    // Wait for error status to appear
    const statusDiv = page.locator('#pdf-upload-status');
    await expect(statusDiv).toBeVisible({ timeout: 5000 });

    // Verify error message indicates authentication issue
    const statusText = await statusDiv.textContent();
    expect(statusText).toBeTruthy();

    // The error should be related to authentication
    // Common messages: "authentication required", "login required", "unauthorized", etc.
    const hasAuthError = statusText.toLowerCase().includes('auth') ||
                        statusText.toLowerCase().includes('login') ||
                        statusText.toLowerCase().includes('sign in') ||
                        responseStatus === 401;

    expect(hasAuthError).toBeTruthy();

    // Clean up
    fs.unlinkSync(pdfFilePath);
  });
});
