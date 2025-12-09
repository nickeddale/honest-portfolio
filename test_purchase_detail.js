const { chromium } = require('playwright');

(async () => {
  console.log('Starting Playwright test for purchase detail view...\n');

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 1280, height: 720 }
  });
  const page = await context.newPage();

  const results = {
    purchaseCardsClickable: false,
    chevronIconPresent: false,
    detailViewLoaded: false,
    headerPresent: false,
    comparisonCardsPresent: false,
    opportunityCostColorCoded: false,
    chartRendered: false,
    tablePresent: false,
    backButtonWorked: false,
    errors: []
  };

  try {
    console.log('1. Navigating to http://localhost:5000...');
    await page.goto('http://localhost:5000', { waitUntil: 'networkidle' });

    console.log('2. Waiting for "Your Purchases" section to be visible...');
    await page.waitForSelector('text=Your Purchases', { timeout: 10000 });
    console.log('   ✓ "Your Purchases" section is visible\n');

    console.log('3. Taking screenshot of initial state...');
    await page.screenshot({ path: '/Users/nickdale/code/honest-portfolio/screenshots/initial-view.png', fullPage: true });
    console.log('   ✓ Screenshot saved to screenshots/initial-view.png\n');

    console.log('4. Checking for purchase cards...');
    // Wait for the purchases section to be visible
    await page.waitForSelector('#purchases-list', { timeout: 10000 });

    // Look for clickable purchase items - they should be in the purchases list
    const purchaseCards = await page.locator('#purchases-list .cursor-pointer').all();
    console.log(`   Found ${purchaseCards.length} purchase cards\n`);

    if (purchaseCards.length === 0) {
      throw new Error('No purchase cards found on the page');
    }

    console.log('5. Checking for chevron icons...');
    const chevrons = await page.locator('svg.lucide-chevron-right').count();
    results.chevronIconPresent = chevrons > 0;
    console.log(`   ${chevrons > 0 ? '✓' : '✗'} Chevron icons present: ${chevrons} found\n`);

    console.log('6. Clicking on the first purchase card...');
    const firstCard = purchaseCards[0];

    // Store the current URL before clicking
    const beforeUrl = page.url();

    await firstCard.click();
    results.purchaseCardsClickable = true;
    console.log('   ✓ Purchase card is clickable\n');

    console.log('7. Verifying URL change to detail view...');
    // Wait for the URL to change to include /purchase/
    await page.waitForFunction(
      (oldUrl) => window.location.href !== oldUrl && window.location.href.includes('#/purchase/'),
      beforeUrl,
      { timeout: 5000 }
    );
    const currentUrl = page.url();
    console.log(`   ✓ URL changed to: ${currentUrl}\n`);

    // Extract purchase ID from the URL
    const purchaseId = currentUrl.split('#/purchase/')[1];
    console.log(`   Purchase ID: ${purchaseId}`);

    console.log('8. Waiting for detail view to load...');
    // First, wait for the loading message
    const loadingVisible = await page.locator('text=Loading purchase details').isVisible().catch(() => false);
    if (loadingVisible) {
      console.log('   ⓘ Loading message displayed');
    }

    // Wait for the detail view content to appear - look for the "Back to Portfolio" button which indicates the view loaded
    await page.waitForSelector('text=Back to Portfolio', { state: 'visible', timeout: 10000 });

    // Wait for the loading message to disappear and actual content to load
    await page.waitForFunction(
      () => !document.body.textContent.includes('Loading purchase details...'),
      { timeout: 15000 }
    ).catch(() => {
      console.log('   ⚠ Loading message still visible after 15s');
    });

    // Give extra time for the data to load
    await page.waitForTimeout(2000);

    results.detailViewLoaded = true;
    console.log('   ✓ Detail view loaded\n');

    console.log('9. Verifying purchase header...');
    // Look for specific elements like "Amount Invested", "Shares Bought", etc.
    const amountInvestedVisible = await page.locator('text=Amount Invested').count() > 0;
    const sharesBoughtVisible = await page.locator('text=Shares Bought').count() > 0;
    results.headerPresent = amountInvestedVisible && sharesBoughtVisible;
    if (results.headerPresent) {
      console.log('   ✓ Header present with purchase details (Amount Invested, Shares Bought)\n');
    } else {
      console.log('   ✗ Header not found\n');
    }

    console.log('10. Verifying comparison cards...');
    // Look for the "If you had bought instead..." section
    const comparisonSectionCount = await page.locator('text=If you had bought instead').count();
    console.log(`   Comparison section found: ${comparisonSectionCount} times`);

    // Count the comparison cards by looking for "You're ahead by" or "You missed out on"
    const aheadCount = await page.locator('text=You\'re ahead by').count();
    const missedCount = await page.locator('text=You missed out on').count();
    const comparisonCardsCount = aheadCount + missedCount;
    results.comparisonCardsPresent = comparisonCardsCount > 0;
    console.log(`   ${comparisonCardsCount > 0 ? '✓' : '✗'} Comparison cards present: ${comparisonCardsCount} found (${aheadCount} ahead, ${missedCount} missed)\n`);

    console.log('11. Checking opportunity cost color coding...');
    const redText = await page.locator('.text-red-600, .text-red-500').count();
    const greenText = await page.locator('.text-green-600, .text-green-500').count();
    results.opportunityCostColorCoded = (redText > 0 || greenText > 0);
    console.log(`   ${results.opportunityCostColorCoded ? '✓' : '✗'} Color coding present (Red: ${redText}, Green: ${greenText})\n`);

    console.log('12. Verifying performance chart...');
    // Wait a moment for the chart to render after detail view loads
    await page.waitForTimeout(1000);
    const canvases = await page.locator('canvas').all();
    // Check if there's at least one canvas
    results.chartRendered = canvases.length >= 1;
    console.log(`   ${canvases.length >= 1 ? '✓' : '✗'} Chart canvas present: ${canvases.length} found\n`);

    console.log('13. Verifying comparison table...');
    // Use first() to avoid strict mode violation
    const tableVisible = await page.locator('h3:has-text("Detailed Comparison")').first().isVisible();
    results.tablePresent = tableVisible;
    console.log(`   ${tableVisible ? '✓' : '✗'} Comparison table present\n`);

    console.log('14. Taking screenshot of detail view...');
    await page.screenshot({ path: '/Users/nickdale/code/honest-portfolio/screenshots/detail-view.png', fullPage: true });
    console.log('   ✓ Screenshot saved to screenshots/detail-view.png\n');

    console.log('15. Testing back button...');
    const backButton = await page.locator('text=Back to Portfolio').first();
    await backButton.click();

    // Wait for the URL hash to change back to root or empty
    await page.waitForFunction(
      () => window.location.hash === '#/' || window.location.hash === '',
      { timeout: 5000 }
    ).catch(() => {
      console.log('   ⚠ URL did not change back to portfolio view');
    });

    // Wait a moment for the view to update
    await page.waitForTimeout(1000);

    // Verify we're back at the portfolio view by checking for the purchases list
    const backToPortfolio = await page.locator('#purchases-list').isVisible().catch(() => false);
    results.backButtonWorked = backToPortfolio;
    console.log(`   ${backToPortfolio ? '✓' : '✗'} Back button works - returned to portfolio view\n`);

    console.log('16. Taking final screenshot...');
    await page.screenshot({ path: '/Users/nickdale/code/honest-portfolio/screenshots/back-to-portfolio.png', fullPage: true });
    console.log('   ✓ Screenshot saved to screenshots/back-to-portfolio.png\n');

  } catch (error) {
    results.errors.push(error.message);
    console.error('\n❌ Error during test:', error.message);
    await page.screenshot({ path: '/Users/nickdale/code/honest-portfolio/screenshots/error-state.png', fullPage: true });
  } finally {
    await browser.close();
  }

  // Print final results
  console.log('\n' + '='.repeat(60));
  console.log('TEST RESULTS SUMMARY');
  console.log('='.repeat(60));
  console.log(`Purchase cards clickable:        ${results.purchaseCardsClickable ? '✓ PASS' : '✗ FAIL'}`);
  console.log(`Chevron icons present:           ${results.chevronIconPresent ? '✓ PASS' : '✗ FAIL'}`);
  console.log(`Detail view loaded:              ${results.detailViewLoaded ? '✓ PASS' : '✗ FAIL'}`);
  console.log(`Header present:                  ${results.headerPresent ? '✓ PASS' : '✗ FAIL'}`);
  console.log(`Comparison cards present:        ${results.comparisonCardsPresent ? '✓ PASS' : '✗ FAIL'}`);
  console.log(`Opportunity cost color-coded:    ${results.opportunityCostColorCoded ? '✓ PASS' : '✗ FAIL'}`);
  console.log(`Chart rendered:                  ${results.chartRendered ? '✓ PASS' : '✗ FAIL'}`);
  console.log(`Comparison table present:        ${results.tablePresent ? '✓ PASS' : '✗ FAIL'}`);
  console.log(`Back button worked:              ${results.backButtonWorked ? '✓ PASS' : '✗ FAIL'}`);
  console.log('='.repeat(60));

  if (results.errors.length > 0) {
    console.log('\nERRORS:');
    results.errors.forEach((err, i) => console.log(`  ${i + 1}. ${err}`));
  }

  const passedTests = Object.entries(results).filter(([key, value]) => key !== 'errors' && value === true).length;
  const totalTests = Object.keys(results).length - 1; // exclude errors array
  console.log(`\nOverall: ${passedTests}/${totalTests} tests passed`);

  process.exit(results.errors.length > 0 ? 1 : 0);
})();
