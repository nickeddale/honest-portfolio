// Honest Portfolio - Main Application
const API_BASE = '/api';

// State
let purchases = [];
let portfolioSummary = null;
let portfolioHistory = null;
let chart = null;

// PDF Upload State
let extractedTrades = [];
let selectedTradeIds = new Set();
// PDF Upload Quota State
let pdfUploadQuota = null;

// Router state
let currentView = 'portfolio'; // 'portfolio' | 'purchase-detail'
let currentPurchaseId = null;
let purchaseDetail = null;
let detailChart = null;

// Security: HTML escaping utility to prevent XSS
function escapeHtml(str) {
    if (str === null || str === undefined) return '';
    const div = document.createElement('div');
    div.textContent = String(str);
    return div.innerHTML;
}

// DOM Elements
// Form elements - Quick Add
const purchaseFormQuick = document.getElementById('purchase-form-quick');
const submitBtnQuick = document.getElementById('submit-btn-quick');

// Form elements - Detailed Entry
const purchaseFormDetailed = document.getElementById('purchase-form-detailed');
const submitBtnDetailed = document.getElementById('submit-btn-detailed');
const quantityInput = document.getElementById('quantity-detailed');
const priceInput = document.getElementById('price-detailed');
const calculatedAmountSpan = document.getElementById('calculated-amount');

// Tab elements
const tabQuickAdd = document.getElementById('tab-quick-add');
const tabDetailedEntry = document.getElementById('tab-detailed-entry');
const tabPdfUpload = document.getElementById('tab-pdf-upload');
const panelQuickAdd = document.getElementById('panel-quick-add');
const panelDetailedEntry = document.getElementById('panel-detailed-entry');
const panelPdfUpload = document.getElementById('panel-pdf-upload');

// Shared form elements
const formError = document.getElementById('form-error');
const formSuccess = document.getElementById('form-success');

const purchasesList = document.getElementById('purchases-list');
const comparisonTbody = document.getElementById('comparison-tbody');
const chartCanvas = document.getElementById('portfolio-chart');
const chartLoading = document.getElementById('chart-loading');

// Skeleton and content sections
const summarySkeleton = document.getElementById('summary-skeleton');
const summarySection = document.getElementById('summary-section');
const chartSkeleton = document.getElementById('chart-skeleton');
const chartSection = document.getElementById('chart-section');
const purchasesSkeleton = document.getElementById('purchases-skeleton');
const purchasesSection = document.getElementById('purchases-section');

// Initialize
document.addEventListener('DOMContentLoaded', init);

function switchTab(tab) {
    // Reset all tabs
    const tabs = [
        { tab: tabQuickAdd, panel: panelQuickAdd, name: 'quick-add' },
        { tab: tabDetailedEntry, panel: panelDetailedEntry, name: 'detailed-entry' },
        { tab: tabPdfUpload, panel: panelPdfUpload, name: 'pdf-upload' }
    ];

    tabs.forEach(({ tab: tabEl, panel, name }) => {
        if (tab === name) {
            // Active tab
            if (tabEl) {
                tabEl.classList.add('text-[var(--primary)]', 'border-[var(--primary)]');
                tabEl.classList.remove('text-[var(--muted-foreground)]', 'border-transparent');
            }
            if (panel) {
                panel.classList.remove('hidden');
            }
        } else {
            // Inactive tab
            if (tabEl) {
                tabEl.classList.remove('text-[var(--primary)]', 'border-[var(--primary)]');
                tabEl.classList.add('text-[var(--muted-foreground)]', 'border-transparent');
            }
            if (panel) {
                panel.classList.add('hidden');
            }
        }
    });
}

function setupDetailedEntryCalculation() {
    const updateCalculatedAmount = () => {
        const quantity = parseFloat(quantityInput.value) || 0;
        const price = parseFloat(priceInput.value) || 0;
        const total = quantity * price;
        calculatedAmountSpan.textContent = formatCurrency(total);
    };

    quantityInput.addEventListener('input', updateCalculatedAmount);
    priceInput.addEventListener('input', updateCalculatedAmount);
}

async function init() {
    // Initialize auth manager and check login status
    await authManager.init();

    // Store auth state for guest mode support
    const isGuest = !authManager.isAuthenticated();

    // Update user UI (handles both guest and authenticated states)
    updateUserUI();

    // Show loading state
    showLoadingState();

    // Set max date to today
    const today = new Date().toISOString().split('T')[0];
    document.getElementById('purchase-date-quick').max = today;
    document.getElementById('purchase-date-detailed').max = today;

    // Load data
    await loadData();

    // Setup form handlers
    purchaseFormQuick.addEventListener('submit', handleQuickAddSubmit);
    purchaseFormDetailed.addEventListener('submit', handleDetailedEntrySubmit);

    // Setup tab switching
    tabQuickAdd.addEventListener('click', () => switchTab('quick-add'));
    tabDetailedEntry.addEventListener('click', () => switchTab('detailed-entry'));
    if (tabPdfUpload) {
        tabPdfUpload.addEventListener('click', () => switchTab('pdf-upload'));
    }

    // Setup auto-calculation for detailed entry
    setupDetailedEntryCalculation();

    // Initialize router
    initRouter();

    // Initialize modal event listeners
    initModalListeners();

    // Initialize static event listeners
    initStaticEventListeners();

    // Initialize PDF upload
    initPdfUpload();

    // Fetch PDF upload quota
    await fetchPdfUploadQuota();

    // Register service worker
    if ('serviceWorker' in navigator) {
        navigator.serviceWorker.register('/static/js/sw.js')
            .then(reg => console.log('Service Worker registered'))
            .catch(err => console.error('Service Worker registration failed:', err));
    }
}

function updateUserUI() {
    const user = authManager.getCurrentUser();
    const userSection = document.getElementById('user-section');
    const guestLoginSection = document.getElementById('guest-login-section');

    if (!user) {
        // Guest mode
        if (userSection) {
            userSection.classList.add('hidden');
        }
        if (guestLoginSection) {
            guestLoginSection.classList.remove('hidden');
        }
        return;
    }

    // Authenticated mode
    if (userSection) {
        userSection.classList.remove('hidden');
    }
    if (guestLoginSection) {
        guestLoginSection.classList.add('hidden');
    }

    const userName = document.getElementById('user-name');
    const userInitials = document.getElementById('user-initials');
    const userPicture = document.getElementById('user-picture');

    if (userName) {
        userName.textContent = user.name;
    }

    if (user.profile_picture) {
        if (userPicture) {
            userPicture.src = user.profile_picture;
            userPicture.classList.remove('hidden');
        }
        if (userInitials) {
            userInitials.classList.add('hidden');
        }
    } else {
        // Show initials
        if (userInitials) {
            const initials = user.name
                .split(' ')
                .map(n => n[0])
                .join('')
                .toUpperCase()
                .slice(0, 2);
            userInitials.textContent = initials;
        }
    }
}

async function loadData() {
    try {
        await Promise.all([
            loadPurchases(),
            loadPortfolioSummary(),
            loadPortfolioHistory()
        ]);
        updateUI();
        hideLoadingState();
    } catch (error) {
        console.error('Error loading data:', error);
        hideLoadingState();
    }
}

async function loadPurchases() {
    try {
        // Guest mode: load from localStorage
        if (!authManager.isAuthenticated()) {
            purchases = guestManager.getGuestPurchases();
            return;
        }

        // Authenticated mode: load from API
        const response = await authManager.authFetch(`${API_BASE}/purchases`);
        if (!response.ok) throw new Error('Failed to load purchases');
        purchases = await response.json();
    } catch (error) {
        if (error.message !== 'Unauthorized') {
            console.error('Error loading purchases:', error);
        }
    }
}

async function loadPortfolioSummary() {
    try {
        // Guest mode: POST purchases to guest endpoint
        if (!authManager.isAuthenticated()) {
            const response = await fetch(`${API_BASE}/guest/portfolio/summary`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    purchases: guestManager.getGuestPurchases()
                })
            });
            if (!response.ok) throw new Error('Failed to load portfolio summary');
            portfolioSummary = await response.json();
            return;
        }

        // Authenticated mode: load from API
        const response = await authManager.authFetch(`${API_BASE}/portfolio/summary`);
        if (!response.ok) throw new Error('Failed to load portfolio summary');
        portfolioSummary = await response.json();
    } catch (error) {
        if (error.message !== 'Unauthorized') {
            console.error('Error loading portfolio summary:', error);
        }
    }
}

async function loadPortfolioHistory() {
    try {
        // Guest mode: POST purchases to guest endpoint
        if (!authManager.isAuthenticated()) {
            const response = await fetch(`${API_BASE}/guest/portfolio/history`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    purchases: guestManager.getGuestPurchases()
                })
            });
            if (!response.ok) throw new Error('Failed to load portfolio history');
            portfolioHistory = await response.json();
            return;
        }

        // Authenticated mode: load from API
        const response = await authManager.authFetch(`${API_BASE}/portfolio/history`);
        if (!response.ok) throw new Error('Failed to load portfolio history');
        portfolioHistory = await response.json();
    } catch (error) {
        if (error.message !== 'Unauthorized') {
            console.error('Error loading portfolio history:', error);
        }
    }
}

function updateUI() {
    renderPurchasesList();
    renderSummaryCards();
    renderComparisonTable();
    renderChart();
}

function showLoadingState() {
    // Show skeleton loaders
    summarySkeleton.classList.remove('hidden');
    chartSkeleton.classList.remove('hidden');
    purchasesSkeleton.classList.remove('hidden');

    // Hide actual content
    summarySection.classList.add('hidden');
    chartSection.classList.add('hidden');
    purchasesSection.classList.add('hidden');

    // Disable the "Add Purchase" buttons
    submitBtnQuick.disabled = true;
    submitBtnDetailed.disabled = true;
}

function hideLoadingState() {
    // Hide skeleton loaders
    summarySkeleton.classList.add('hidden');
    chartSkeleton.classList.add('hidden');
    purchasesSkeleton.classList.add('hidden');

    // Show actual content
    summarySection.classList.remove('hidden');
    chartSection.classList.remove('hidden');
    purchasesSection.classList.remove('hidden');

    // Enable the "Add Purchase" buttons
    submitBtnQuick.disabled = false;
    submitBtnDetailed.disabled = false;
}

async function handleQuickAddSubmit(e) {
    e.preventDefault();

    hideMessages();
    submitBtnQuick.disabled = true;
    submitBtnQuick.textContent = 'Adding...';

    const formData = new FormData(purchaseFormQuick);
    const data = {
        ticker: formData.get('ticker').toUpperCase(),
        purchase_date: formData.get('purchase_date'),
        amount: parseFloat(formData.get('amount')),
        entry_mode: 'quick'
    };

    try {
        // Guest mode: validate and save to localStorage
        if (!authManager.isAuthenticated()) {
            const response = await fetch(`${API_BASE}/guest/purchases/validate`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(data)
            });

            const result = await response.json();

            if (!response.ok) {
                showError(result.error || 'Failed to add purchase');
                return;
            }

            // Save to localStorage
            guestManager.addGuestPurchase(result);

            showSuccess(`Added $${data.amount.toFixed(2)} investment in ${data.ticker}`);
            purchaseFormQuick.reset();

            // Show signup prompt if needed
            showGuestSignupPrompt();

            await loadData();
        } else {
            // Authenticated mode: use existing API
            const response = await authManager.authFetch(`${API_BASE}/purchases`, {
                method: 'POST',
                body: JSON.stringify(data)
            });

            const result = await response.json();

            if (!response.ok) {
                showError(result.error || 'Failed to add purchase');
                return;
            }

            showSuccess(`Added $${data.amount.toFixed(2)} investment in ${data.ticker}`);
            purchaseFormQuick.reset();
            await loadData();
        }
    } catch (error) {
        showError('Network error. Please try again.');
    } finally {
        submitBtnQuick.disabled = false;
        submitBtnQuick.textContent = 'Add Purchase';
    }
}

async function handleDetailedEntrySubmit(e) {
    e.preventDefault();

    hideMessages();
    submitBtnDetailed.disabled = true;
    submitBtnDetailed.textContent = 'Adding...';

    const formData = new FormData(purchaseFormDetailed);
    const quantity = parseFloat(formData.get('quantity'));
    const pricePerShare = parseFloat(formData.get('price_per_share'));
    const data = {
        ticker: formData.get('ticker').toUpperCase(),
        purchase_date: formData.get('purchase_date'),
        quantity: quantity,
        price_per_share: pricePerShare,
        entry_mode: 'detailed'
    };

    try {
        // Guest mode: validate and save to localStorage
        if (!authManager.isAuthenticated()) {
            const response = await fetch(`${API_BASE}/guest/purchases/validate`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(data)
            });

            const result = await response.json();

            if (!response.ok) {
                showError(result.error || 'Failed to add purchase');
                return;
            }

            // Save to localStorage
            guestManager.addGuestPurchase(result);

            const amount = quantity * pricePerShare;
            showSuccess(`Added ${quantity.toFixed(4)} shares of ${data.ticker} at ${formatCurrency(pricePerShare)} per share`);
            purchaseFormDetailed.reset();
            calculatedAmountSpan.textContent = '$0.00';

            // Show signup prompt if needed
            showGuestSignupPrompt();

            await loadData();
        } else {
            // Authenticated mode: use existing API
            const response = await authManager.authFetch(`${API_BASE}/purchases`, {
                method: 'POST',
                body: JSON.stringify(data)
            });

            const result = await response.json();

            if (!response.ok) {
                showError(result.error || 'Failed to add purchase');
                return;
            }

            const amount = quantity * pricePerShare;
            showSuccess(`Added ${quantity.toFixed(4)} shares of ${data.ticker} at ${formatCurrency(pricePerShare)} per share`);
            purchaseFormDetailed.reset();
            calculatedAmountSpan.textContent = '$0.00';
            await loadData();
        }
    } catch (error) {
        showError('Network error. Please try again.');
    } finally {
        submitBtnDetailed.disabled = false;
        submitBtnDetailed.textContent = 'Add Purchase';
    }
}

async function deletePurchase(id) {
    const confirmed = await showConfirmation({
        title: 'Delete Purchase',
        message: 'Are you sure you want to delete this purchase? This action cannot be undone.',
        confirmText: 'Delete',
        cancelText: 'Cancel',
        type: 'danger'
    });

    if (!confirmed) return;

    try {
        // Guest mode: check if it's a guest purchase
        if (String(id).startsWith('guest_')) {
            guestManager.deleteGuestPurchase(id);
            showToast('Purchase deleted successfully', 'success');
            await loadData();
        } else {
            // Authenticated mode: use API
            await authManager.authFetch(`${API_BASE}/purchases/${id}`, { method: 'DELETE' });
            showToast('Purchase deleted successfully', 'success');
            await loadData();
        }
    } catch (error) {
        showToast('Failed to delete purchase', 'error');
    }
}

function renderPurchasesList() {
    if (purchases.length === 0) {
        purchasesList.innerHTML = '<p class="text-[var(--muted-foreground)]">No purchases yet</p>';
        return;
    }

    purchasesList.innerHTML = purchases.map(p => `
        <div class="purchase-item flex items-center justify-between p-3 bg-[var(--card)] border-2 border-[var(--border)] rounded shadow-md hover:shadow-none cursor-pointer transition-all"
             data-purchase-id="${p.id}">
            <div>
                <span class="font-semibold text-[var(--card-foreground)]">${escapeHtml(p.ticker)}</span>
                <span class="text-[var(--muted-foreground)] text-sm ml-2">${formatDate(p.purchase_date)}</span>
            </div>
            <div class="flex items-center gap-4">
                <span class="text-[var(--card-foreground)]">${formatCurrency(p.amount)}</span>
                <span class="text-[var(--muted-foreground)] text-sm">${p.shares_bought.toFixed(4)} shares @ ${formatCurrency(p.price_at_purchase)}</span>
                <button class="delete-purchase-btn p-1 border-2 border-[var(--border)] rounded shadow-md hover:shadow-none hover:translate-y-0.5 transition-all text-[var(--destructive)]"
                        data-delete-id="${p.id}">
                    <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                    </svg>
                </button>
                <svg class="w-5 h-5 text-[var(--muted-foreground)]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
                </svg>
            </div>
        </div>
    `).join('');
}

function renderSummaryCards() {
    if (!portfolioSummary) return;

    const { actual, alternatives } = portfolioSummary;

    // Total invested
    document.getElementById('total-invested').textContent = formatCurrency(actual.total_invested);

    // Actual portfolio value
    document.getElementById('actual-value').textContent = formatCurrency(actual.current_value);
    document.getElementById('actual-return').textContent =
        `${actual.gain_loss >= 0 ? '+' : ''}${formatCurrency(actual.gain_loss)} (${actual.return_pct.toFixed(2)}%)`;
    document.getElementById('actual-return').className =
        `text-sm ${actual.gain_loss >= 0 ? 'text-[var(--success)]' : 'text-[var(--destructive)]'}`;

    // Best alternative
    if (alternatives.length > 0) {
        const best = alternatives.reduce((a, b) => a.current_value > b.current_value ? a : b);
        document.getElementById('best-alt-value').textContent = formatCurrency(best.current_value);
        document.getElementById('best-alt-name').textContent = `${best.name} (${best.ticker})`;

        // Opportunity cost
        const oppCost = best.current_value - actual.current_value;
        document.getElementById('opportunity-cost').textContent = formatCurrency(Math.abs(oppCost));
        document.getElementById('opportunity-cost').className =
            `text-2xl font-bold ${oppCost > 0 ? 'text-[var(--destructive)]' : 'text-[var(--success)]'}`;
        document.getElementById('opportunity-cost-desc').textContent =
            oppCost > 0 ? `You could have earned more with ${best.ticker}` : 'Your picks are outperforming!';
    }

    // Show share button when there's data
    const shareButtonSection = document.getElementById('share-button-section');
    if (shareButtonSection && actual.total_invested > 0) {
        shareButtonSection.classList.remove('hidden');
    }
}

function renderComparisonTable() {
    if (!portfolioSummary || portfolioSummary.actual.total_invested === 0) {
        comparisonTbody.innerHTML = '<tr><td colspan="5" class="px-6 py-4 text-center text-[var(--muted-foreground)]">No purchases yet</td></tr>';
        return;
    }

    const { actual, alternatives } = portfolioSummary;

    // Combine actual and alternatives
    const rows = [
        {
            name: 'Your Portfolio',
            ticker: 'ACTUAL',
            isActual: true,
            ...actual
        },
        ...alternatives.map(a => ({ ...a, isActual: false }))
    ];

    // Sort by current value descending
    rows.sort((a, b) => b.current_value - a.current_value);

    comparisonTbody.innerHTML = rows.map((row, idx) => `
        <tr class="border-b border-[var(--border)] hover:bg-[var(--primary)]/10 transition-colors ${row.isActual ? 'bg-[var(--primary)]/5' : ''} ${idx === 0 ? 'ring-2 ring-[var(--success)]' : ''}">
            <td class="px-6 py-4 whitespace-nowrap">
                <div class="flex items-center">
                    ${idx === 0 ? '<span class="text-[var(--success)] mr-2">👑</span>' : ''}
                    <span class="font-medium ${row.isActual ? 'text-[var(--primary)]' : 'text-[var(--foreground)]'}">${escapeHtml(row.name || row.ticker)}</span>
                    ${row.isActual ? '<span class="ml-2 px-2 py-1 text-xs border-2 border-[var(--border)] rounded bg-[var(--primary)]/10 text-[var(--primary)]">You</span>' : ''}
                </div>
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-right text-[var(--muted-foreground)]">${formatCurrency(row.total_invested)}</td>
            <td class="px-6 py-4 whitespace-nowrap text-right font-medium text-[var(--foreground)]">${formatCurrency(row.current_value)}</td>
            <td class="px-6 py-4 whitespace-nowrap text-right ${row.gain_loss >= 0 ? 'text-[var(--success)]' : 'text-[var(--destructive)]'}">
                ${row.gain_loss >= 0 ? '+' : ''}${formatCurrency(row.gain_loss)}
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-right ${row.return_pct >= 0 ? 'text-[var(--success)]' : 'text-[var(--destructive)]'}">
                ${row.return_pct >= 0 ? '+' : ''}${row.return_pct.toFixed(2)}%
            </td>
        </tr>
    `).join('');
}

function renderChart() {
    if (!portfolioHistory || portfolioHistory.dates.length === 0) {
        chartCanvas.classList.add('hidden');
        chartLoading.classList.remove('hidden');
        return;
    }

    chartCanvas.classList.remove('hidden');
    chartLoading.classList.add('hidden');

    const colors = {
        'ACTUAL': { border: '#2563eb', bg: 'rgba(37, 99, 235, 0.1)' },
        'SPY': { border: '#6b7280', bg: 'rgba(107, 114, 128, 0.1)' },
        'AAPL': { border: '#10b981', bg: 'rgba(16, 185, 129, 0.1)' },
        'META': { border: '#3b82f6', bg: 'rgba(59, 130, 246, 0.1)' },
        'GOOGL': { border: '#f59e0b', bg: 'rgba(245, 158, 11, 0.1)' },
        'NVDA': { border: '#84cc16', bg: 'rgba(132, 204, 22, 0.1)' },
        'AMZN': { border: '#f97316', bg: 'rgba(249, 115, 22, 0.1)' }
    };

    const datasets = [
        {
            label: 'Your Portfolio',
            data: portfolioHistory.actual,
            borderColor: colors.ACTUAL.border,
            backgroundColor: colors.ACTUAL.bg,
            borderWidth: 3,
            fill: false,
            tension: 0.1
        }
    ];

    // Add alternatives
    for (const [ticker, values] of Object.entries(portfolioHistory.alternatives)) {
        const color = colors[ticker] || { border: '#9ca3af', bg: 'rgba(156, 163, 175, 0.1)' };
        datasets.push({
            label: ticker,
            data: values,
            borderColor: color.border,
            backgroundColor: color.bg,
            borderWidth: 2,
            fill: false,
            tension: 0.1
        });
    }

    // Destroy existing chart
    if (chart) {
        chart.destroy();
    }

    chart = new Chart(chartCanvas, {
        type: 'line',
        data: {
            labels: portfolioHistory.dates.map(d => formatDate(d)),
            datasets: datasets
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: {
                    position: 'bottom'
                },
                tooltip: {
                    mode: 'index',
                    intersect: false,
                    callbacks: {
                        label: function(context) {
                            return `${context.dataset.label}: ${formatCurrency(context.raw)}`;
                        }
                    }
                }
            },
            scales: {
                x: {
                    display: true,
                    title: { display: true, text: 'Date' }
                },
                y: {
                    display: true,
                    title: { display: true, text: 'Value (USD)' },
                    ticks: {
                        callback: function(value) {
                            return formatCurrency(value);
                        }
                    }
                }
            },
            interaction: {
                mode: 'nearest',
                axis: 'x',
                intersect: false
            }
        }
    });
}

// Utility functions
function formatCurrency(value) {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD'
    }).format(value);
}

function formatDate(dateStr) {
    return new Date(dateStr).toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric'
    });
}

// Toast Notification System
function showToast(message, type = 'info', duration = 4000) {
    const container = document.getElementById('toast-container');

    const toast = document.createElement('div');
    toast.className = `pointer-events-auto flex items-center gap-3 px-4 py-3 rounded shadow-md transform transition-all duration-300 translate-x-full opacity-0 max-w-sm`;

    // Type-specific styles
    const styles = {
        success: { bg: 'bg-green-100 border-2 border-[var(--success)]', icon: 'text-green-600', iconPath: 'M5 13l4 4L19 7' },
        error: { bg: 'bg-red-100 border-2 border-[var(--destructive)]', icon: 'text-red-600', iconPath: 'M6 18L18 6M6 6l12 12' },
        warning: { bg: 'bg-yellow-100 border-2 border-yellow-600', icon: 'text-yellow-600', iconPath: 'M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z' },
        info: { bg: 'bg-blue-100 border-2 border-[var(--primary)]', icon: 'text-blue-600', iconPath: 'M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z' }
    };

    const style = styles[type] || styles.info;
    toast.classList.add(...style.bg.split(' '));

    toast.innerHTML = `
        <svg class="w-5 h-5 flex-shrink-0 ${style.icon}" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="${style.iconPath}"/>
        </svg>
        <span class="text-sm font-medium text-[var(--foreground)] flex-1">${escapeHtml(message)}</span>
        <button class="toast-close-btn text-[var(--muted-foreground)] hover:text-[var(--foreground)] flex-shrink-0">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
            </svg>
        </button>
    `;

    container.appendChild(toast);

    // Trigger animation
    requestAnimationFrame(() => {
        toast.classList.remove('translate-x-full', 'opacity-0');
    });

    // Auto-remove after duration
    setTimeout(() => {
        toast.classList.add('translate-x-full', 'opacity-0');
        setTimeout(() => toast.remove(), 300);
    }, duration);
}

// Confirmation Modal System
let confirmationResolver = null;

function showConfirmation({ title = 'Confirm Action', message = 'Are you sure?', confirmText = 'Confirm', cancelText = 'Cancel', type = 'danger' } = {}) {
    return new Promise((resolve) => {
        confirmationResolver = resolve;

        const modal = document.getElementById('confirmation-modal');
        const modalTitle = document.getElementById('modal-title');
        const modalMessage = document.getElementById('modal-message');
        const modalConfirm = document.getElementById('modal-confirm');
        const modalCancel = document.getElementById('modal-cancel');
        const modalIcon = document.getElementById('modal-icon');

        modalTitle.textContent = title;
        modalMessage.textContent = message;
        modalConfirm.textContent = confirmText;
        modalCancel.textContent = cancelText;

        // Apply type-specific styling
        if (type === 'danger') {
            modalIcon.className = 'flex-shrink-0 w-10 h-10 rounded-full bg-red-100 border-2 border-[var(--destructive)] flex items-center justify-center';
            modalIcon.innerHTML = `<svg class="w-6 h-6 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/>
            </svg>`;
            modalConfirm.className = 'px-4 py-2 text-sm font-medium text-white bg-[var(--destructive)] border-2 border-[var(--border)] rounded shadow-md hover:shadow-none hover:translate-y-0.5 transition-all';
        } else {
            modalIcon.className = 'flex-shrink-0 w-10 h-10 rounded-full bg-blue-100 border-2 border-[var(--primary)] flex items-center justify-center';
            modalIcon.innerHTML = `<svg class="w-6 h-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
            </svg>`;
            modalConfirm.className = 'px-4 py-2 text-sm font-medium text-white bg-[var(--primary)] border-2 border-[var(--border)] rounded shadow-md hover:shadow-none hover:translate-y-0.5 transition-all';
        }

        modal.classList.remove('hidden');
        document.body.style.overflow = 'hidden';

        // Focus the cancel button for safety
        modalCancel.focus();
    });
}

function closeConfirmation(result) {
    const modal = document.getElementById('confirmation-modal');
    modal.classList.add('hidden');
    document.body.style.overflow = '';

    if (confirmationResolver) {
        confirmationResolver(result);
        confirmationResolver = null;
    }
}

// Initialize modal event listeners
function initModalListeners() {
    const modal = document.getElementById('confirmation-modal');
    const backdrop = document.getElementById('modal-backdrop');
    const cancelBtn = document.getElementById('modal-cancel');
    const confirmBtn = document.getElementById('modal-confirm');

    backdrop.addEventListener('click', () => closeConfirmation(false));
    cancelBtn.addEventListener('click', () => closeConfirmation(false));
    confirmBtn.addEventListener('click', () => closeConfirmation(true));

    // Keyboard support
    document.addEventListener('keydown', (e) => {
        if (!modal.classList.contains('hidden')) {
            if (e.key === 'Escape') {
                closeConfirmation(false);
            }
        }
    });
}

function initStaticEventListeners() {
    // Logout button
    const logoutBtn = document.getElementById('logout-btn');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', () => authManager.logout());
    }

    // Share results button
    const shareResultsBtn = document.getElementById('share-results-btn');
    if (shareResultsBtn) {
        shareResultsBtn.addEventListener('click', openShareModal);
    }

    // Navigate back button
    const navigateBackBtn = document.getElementById('navigate-back-btn');
    if (navigateBackBtn) {
        navigateBackBtn.addEventListener('click', navigateBack);
    }

    // Share modal backdrop
    const shareModalBackdrop = document.getElementById('share-modal-backdrop');
    if (shareModalBackdrop) {
        shareModalBackdrop.addEventListener('click', closeShareModal);
    }

    // Share modal close button
    const shareModalCloseBtn = document.getElementById('share-modal-close-btn');
    if (shareModalCloseBtn) {
        shareModalCloseBtn.addEventListener('click', closeShareModal);
    }

    // Download share image button
    const downloadShareBtn = document.getElementById('download-share-btn');
    if (downloadShareBtn) {
        downloadShareBtn.addEventListener('click', downloadShareImage);
    }

    // Copy share link button
    const copyShareLinkBtn = document.getElementById('copy-share-link-btn');
    if (copyShareLinkBtn) {
        copyShareLinkBtn.addEventListener('click', copyShareLink);
    }

    // Dismiss guest prompt button
    const dismissGuestPromptBtn = document.getElementById('dismiss-guest-prompt-btn');
    if (dismissGuestPromptBtn) {
        dismissGuestPromptBtn.addEventListener('click', dismissGuestPrompt);
    }

    // Google sign-in buttons (multiple)
    document.querySelectorAll('.google-signin-btn').forEach(btn => {
        btn.addEventListener('click', () => authManager.loginWith('google'));
    });

    // Event delegation for purchases list (dynamic content)
    const purchasesList = document.getElementById('purchases-list');
    if (purchasesList) {
        purchasesList.addEventListener('click', (e) => {
            // Handle delete button click
            const deleteBtn = e.target.closest('.delete-purchase-btn');
            if (deleteBtn) {
                e.stopPropagation();
                const purchaseId = deleteBtn.dataset.deleteId;
                if (purchaseId) {
                    // Handle both numeric and guest_ prefixed IDs
                    const id = purchaseId.startsWith('guest_') ? purchaseId : parseInt(purchaseId);
                    deletePurchase(id);
                }
                return;
            }

            // Handle purchase item click
            const purchaseItem = e.target.closest('.purchase-item');
            if (purchaseItem) {
                const purchaseId = purchaseItem.dataset.purchaseId;
                if (purchaseId) {
                    const id = purchaseId.startsWith('guest_') ? purchaseId : parseInt(purchaseId);
                    navigateToPurchase(id);
                }
            }
        });
    }

    // Event delegation for toast close buttons (dynamic content)
    const toastContainer = document.getElementById('toast-container');
    if (toastContainer) {
        toastContainer.addEventListener('click', (e) => {
            const closeBtn = e.target.closest('.toast-close-btn');
            if (closeBtn) {
                const toast = closeBtn.closest('.pointer-events-auto');
                if (toast) {
                    toast.remove();
                }
            }
        });
    }
}

function showError(message) {
    showToast(message, 'error');
}

function showSuccess(message) {
    showToast(message, 'success');
}

function hideMessages() {
    formError.classList.add('hidden');
    formSuccess.classList.add('hidden');
}

// Guest signup prompt functions
function showGuestSignupPrompt() {
    if (!guestManager.shouldShowPrompt()) return;

    const prompt = document.getElementById('guest-signup-prompt');
    if (prompt) {
        prompt.classList.remove('hidden');
    }
}

function dismissGuestPrompt() {
    guestManager.dismissPrompt();
    const prompt = document.getElementById('guest-signup-prompt');
    if (prompt) {
        prompt.classList.add('hidden');
    }
}

// Router functions
function initRouter() {
    window.addEventListener('hashchange', handleRouteChange);
    handleRouteChange(); // Handle initial route
}

function handleRouteChange() {
    const hash = window.location.hash;

    if (hash.startsWith('#/purchase/')) {
        const id = parseInt(hash.split('/')[2]);
        if (!isNaN(id)) {
            showPurchaseDetail(id);
            return;
        }
    }

    // Default: show portfolio view
    showPortfolioView();
}

function navigateTo(path) {
    window.location.hash = path;
}

function navigateBack() {
    window.location.hash = '';
}

function navigateToPurchase(id) {
    navigateTo(`/purchase/${id}`);
}

// View switching functions
function showPortfolioView() {
    currentView = 'portfolio';
    currentPurchaseId = null;

    // Show portfolio sections
    document.getElementById('add-purchase-section').classList.remove('hidden');
    document.getElementById('summary-section').classList.remove('hidden');
    document.getElementById('chart-section').classList.remove('hidden');
    document.getElementById('table-section').classList.remove('hidden');
    document.getElementById('purchases-section').classList.remove('hidden');

    // Show share button if there's data
    const shareButtonSection = document.getElementById('share-button-section');
    if (shareButtonSection && portfolioSummary && portfolioSummary.actual.total_invested > 0) {
        shareButtonSection.classList.remove('hidden');
    }

    // Hide detail section
    document.getElementById('purchase-detail-section').classList.add('hidden');
}

function showPurchaseDetail(purchaseId) {
    currentView = 'purchase-detail';
    currentPurchaseId = purchaseId;

    // Hide portfolio sections
    document.getElementById('add-purchase-section').classList.add('hidden');
    document.getElementById('summary-section').classList.add('hidden');
    document.getElementById('chart-section').classList.add('hidden');
    document.getElementById('table-section').classList.add('hidden');
    document.getElementById('purchases-section').classList.add('hidden');

    // Hide share button
    const shareButtonSection = document.getElementById('share-button-section');
    if (shareButtonSection) {
        shareButtonSection.classList.add('hidden');
    }

    // Show detail section
    document.getElementById('purchase-detail-section').classList.remove('hidden');

    // Reset detail view state
    document.getElementById('detail-loading').classList.remove('hidden');
    document.getElementById('detail-content').classList.add('hidden');
    document.getElementById('detail-error').classList.add('hidden');

    // Load and render detail data
    loadPurchaseDetail(purchaseId);
}

// Purchase detail data loading and rendering
async function loadPurchaseDetail(purchaseId) {
    try {
        const response = await authManager.authFetch(`${API_BASE}/purchases/${purchaseId}/comparison`);
        if (!response.ok) {
            if (response.status === 404) {
                showDetailError('Purchase not found');
                return;
            }
            throw new Error('Failed to load purchase details');
        }
        purchaseDetail = await response.json();
        renderPurchaseDetail();
    } catch (error) {
        showDetailError(error.message);
    }
}

function renderPurchaseDetail() {
    document.getElementById('detail-loading').classList.add('hidden');
    document.getElementById('detail-content').classList.remove('hidden');

    const { purchase, actual, alternatives, history } = purchaseDetail;

    // Header info
    document.getElementById('detail-ticker').textContent = purchase.ticker;
    document.getElementById('detail-date').textContent = formatDate(purchase.purchase_date);
    document.getElementById('detail-amount').textContent = formatCurrency(purchase.amount);
    document.getElementById('detail-shares').textContent = purchase.shares_bought.toFixed(4);
    document.getElementById('detail-price-at-purchase').textContent = formatCurrency(purchase.price_at_purchase);
    document.getElementById('detail-current-value').textContent = formatCurrency(actual.current_value);

    const returnClass = actual.gain_loss >= 0 ? 'text-[var(--success)]' : 'text-[var(--destructive)]';
    document.getElementById('detail-return').className = `text-sm ${returnClass}`;
    document.getElementById('detail-return').textContent =
        `${actual.gain_loss >= 0 ? '+' : ''}${formatCurrency(actual.gain_loss)} (${actual.return_pct.toFixed(2)}%)`;

    // Alternative cards
    renderAlternativeCards(alternatives, actual);

    // Comparison table
    renderDetailComparisonTable(purchase, actual, alternatives);

    // Chart
    renderDetailChart(history);
}

function renderAlternativeCards(alternatives, actual) {
    const container = document.getElementById('detail-alternatives');

    container.innerHTML = alternatives.map(alt => {
        const diff = alt.current_value - actual.current_value;
        const diffClass = diff > 0 ? 'text-[var(--destructive)]' : 'text-[var(--success)]';
        const borderClass = diff > 0 ? 'border-2 border-[var(--destructive)] bg-red-50' : 'border-2 border-[var(--success)] bg-green-50';
        const diffText = diff > 0
            ? `You missed out on ${formatCurrency(diff)}`
            : `You're ahead by ${formatCurrency(Math.abs(diff))}`;

        return `
            <div class="${borderClass} rounded shadow-md p-4 transition-all hover:shadow-none">
                <div class="flex justify-between items-start mb-2">
                    <div>
                        <span class="font-semibold text-[var(--foreground)]">${escapeHtml(alt.ticker)}</span>
                        <span class="text-[var(--muted-foreground)] text-sm block">${escapeHtml(alt.name)}</span>
                    </div>
                    <span class="text-lg font-bold ${alt.return_pct >= 0 ? 'text-[var(--success)]' : 'text-[var(--destructive)]'}">
                        ${alt.return_pct >= 0 ? '+' : ''}${alt.return_pct.toFixed(2)}%
                    </span>
                </div>
                <p class="text-[var(--muted-foreground)] text-sm">
                    Would be worth <span class="font-semibold">${formatCurrency(alt.current_value)}</span>
                </p>
                <p class="${diffClass} text-sm font-medium mt-1">${diffText}</p>
            </div>
        `;
    }).join('');
}

function renderDetailComparisonTable(purchase, actual, alternatives) {
    const tbody = document.getElementById('detail-comparison-tbody');

    // Build rows array with actual purchase first
    const rows = [
        {
            ticker: purchase.ticker,
            name: 'Your Purchase',
            isActual: true,
            price_at_purchase: purchase.price_at_purchase,
            shares: purchase.shares_bought,
            current_price: actual.current_price,
            current_value: actual.current_value,
            return_pct: actual.return_pct,
            difference: 0
        },
        ...alternatives.map(alt => ({
            ticker: alt.ticker,
            name: alt.name,
            isActual: false,
            price_at_purchase: alt.price_at_purchase,
            shares: alt.shares_would_have,
            current_price: alt.current_price,
            current_value: alt.current_value,
            return_pct: alt.return_pct,
            difference: alt.difference_vs_actual
        }))
    ];

    // Sort by current value descending
    rows.sort((a, b) => b.current_value - a.current_value);

    tbody.innerHTML = rows.map((row, idx) => `
        <tr class="border-b border-[var(--border)] hover:bg-[var(--primary)]/10 transition-colors ${row.isActual ? 'bg-[var(--primary)]/5' : ''} ${idx === 0 ? 'ring-2 ring-[var(--success)]' : ''}">
            <td class="px-6 py-4 whitespace-nowrap">
                <div class="flex items-center">
                    ${idx === 0 ? '<span class="text-[var(--success)] mr-2">👑</span>' : ''}
                    <span class="font-medium ${row.isActual ? 'text-[var(--primary)]' : 'text-[var(--foreground)]'}">${escapeHtml(row.isActual ? row.name : row.name || row.ticker)}</span>
                    ${row.isActual ? '<span class="ml-2 px-2 py-1 text-xs border-2 border-[var(--border)] rounded bg-[var(--primary)]/10 text-[var(--primary)]">You</span>' : ''}
                </div>
            </td>
            <td class="px-6 py-4 text-right text-[var(--muted-foreground)]">${formatCurrency(row.price_at_purchase)}</td>
            <td class="px-6 py-4 text-right text-[var(--muted-foreground)]">${row.shares.toFixed(4)}</td>
            <td class="px-6 py-4 text-right text-[var(--muted-foreground)]">${formatCurrency(row.current_price)}</td>
            <td class="px-6 py-4 text-right font-medium text-[var(--foreground)]">${formatCurrency(row.current_value)}</td>
            <td class="px-6 py-4 text-right ${row.return_pct >= 0 ? 'text-[var(--success)]' : 'text-[var(--destructive)]'}">
                ${row.return_pct >= 0 ? '+' : ''}${row.return_pct.toFixed(2)}%
            </td>
            <td class="px-6 py-4 text-right ${row.difference > 0 ? 'text-[var(--destructive)]' : row.difference < 0 ? 'text-[var(--success)]' : 'text-[var(--muted-foreground)]'}">
                ${row.isActual ? '-' : (row.difference > 0 ? '+' : '') + formatCurrency(row.difference)}
            </td>
        </tr>
    `).join('');
}

function renderDetailChart(history) {
    const canvas = document.getElementById('detail-chart');

    if (detailChart) {
        detailChart.destroy();
    }

    const colors = {
        'ACTUAL': { border: '#2563eb', bg: 'rgba(37, 99, 235, 0.1)' },
        'SPY': { border: '#6b7280', bg: 'rgba(107, 114, 128, 0.1)' },
        'AAPL': { border: '#10b981', bg: 'rgba(16, 185, 129, 0.1)' },
        'META': { border: '#3b82f6', bg: 'rgba(59, 130, 246, 0.1)' },
        'GOOGL': { border: '#f59e0b', bg: 'rgba(245, 158, 11, 0.1)' },
        'NVDA': { border: '#84cc16', bg: 'rgba(132, 204, 22, 0.1)' },
        'AMZN': { border: '#f97316', bg: 'rgba(249, 115, 22, 0.1)' }
    };

    const datasets = [
        {
            label: 'Your Purchase',
            data: history.actual,
            borderColor: colors.ACTUAL.border,
            backgroundColor: colors.ACTUAL.bg,
            borderWidth: 3,
            fill: false,
            tension: 0.1
        }
    ];

    for (const [ticker, values] of Object.entries(history.alternatives)) {
        const color = colors[ticker] || { border: '#9ca3af', bg: 'rgba(156, 163, 175, 0.1)' };
        datasets.push({
            label: ticker,
            data: values,
            borderColor: color.border,
            backgroundColor: color.bg,
            borderWidth: 2,
            fill: false,
            tension: 0.1
        });
    }

    detailChart = new Chart(canvas, {
        type: 'line',
        data: {
            labels: history.dates.map(d => formatDate(d)),
            datasets: datasets
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: { position: 'bottom' },
                tooltip: {
                    mode: 'index',
                    intersect: false,
                    callbacks: {
                        label: function(context) {
                            return `${context.dataset.label}: ${formatCurrency(context.raw)}`;
                        }
                    }
                }
            },
            scales: {
                x: { display: true, title: { display: true, text: 'Date' } },
                y: {
                    display: true,
                    title: { display: true, text: 'Value (USD)' },
                    ticks: {
                        callback: function(value) { return formatCurrency(value); }
                    }
                }
            },
            interaction: {
                mode: 'nearest',
                axis: 'x',
                intersect: false
            }
        }
    });
}

function showDetailError(message) {
    document.getElementById('detail-loading').classList.add('hidden');
    document.getElementById('detail-error').classList.remove('hidden');
    document.getElementById('detail-error').textContent = message;
}

// Share functionality
let currentShareToken = null;

async function openShareModal() {
    const modal = document.getElementById('share-modal');
    const shareUrlInput = document.getElementById('share-url');
    const sharePreview = document.getElementById('share-preview');

    modal.classList.remove('hidden');
    document.body.style.overflow = 'hidden';

    // Show loading state in preview
    sharePreview.innerHTML = '<div class="text-center text-gray-500">Loading preview...</div>';

    // Create share token if not exists
    if (!currentShareToken) {
        try {
            const response = await authManager.authFetch(`${API_BASE}/share/create`, {
                method: 'POST'
            });

            if (!response.ok) {
                throw new Error('Failed to create share link');
            }

            const data = await response.json();
            currentShareToken = data.share_token;
            shareUrlInput.value = data.share_url;
        } catch (error) {
            showToast('Failed to create share link', 'error');
            closeShareModal();
            return;
        }
    }

    // Render preview
    renderSharePreview();
}

function closeShareModal() {
    const modal = document.getElementById('share-modal');
    modal.classList.add('hidden');
    document.body.style.overflow = '';
}

async function downloadShareImage() {
    if (!currentShareToken) {
        showToast('No share token available', 'error');
        return;
    }

    try {
        const response = await authManager.authFetch(`${API_BASE}/share/${currentShareToken}/image`);

        if (!response.ok) {
            throw new Error('Failed to download image');
        }

        const blob = await response.blob();
        const url = URL.createObjectURL(blob);

        const a = document.createElement('a');
        a.href = url;
        a.download = 'portfolio-summary.png';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);

        setTimeout(() => URL.revokeObjectURL(url), 100);
        showToast('Image downloaded successfully', 'success');
    } catch (error) {
        console.error('Download error:', error);
        showToast('Failed to download image', 'error');
    }
}

function copyShareLink() {
    const shareUrlInput = document.getElementById('share-url');

    shareUrlInput.select();
    shareUrlInput.setSelectionRange(0, 99999); // For mobile devices

    navigator.clipboard.writeText(shareUrlInput.value)
        .then(() => {
            showToast('Link copied to clipboard', 'success');
        })
        .catch(() => {
            showToast('Failed to copy link', 'error');
        });
}

function renderSharePreview() {
    if (!portfolioSummary) {
        return;
    }

    const sharePreview = document.getElementById('share-preview');
    const { actual, alternatives } = portfolioSummary;

    // Find SPY
    const spy = alternatives.find(a => a.ticker === 'SPY');

    // Find best and worst benchmarks
    const best = alternatives.reduce((a, b) => a.return_pct > b.return_pct ? a : b);
    const worst = alternatives.reduce((a, b) => a.return_pct < b.return_pct ? a : b);

    // Calculate opportunity cost (vs best alternative)
    const opportunityCost = best.current_value - actual.current_value;

    // Color classes
    const yourReturnClass = actual.return_pct >= 0 ? 'text-green-600' : 'text-red-600';
    const bestReturnClass = best.return_pct >= 0 ? 'text-green-600' : 'text-red-600';
    const worstReturnClass = worst.return_pct >= 0 ? 'text-green-600' : 'text-red-600';
    const oppCostClass = opportunityCost > 0 ? 'text-red-600' : 'text-green-600';

    sharePreview.innerHTML = `
        <div class="bg-gradient-to-br from-blue-500 to-purple-600 p-6 border-2 border-[var(--border)] rounded shadow-md text-white">
            <h3 class="text-2xl font-bold mb-4">My Portfolio Performance</h3>

            <div class="bg-white/10 backdrop-blur-sm border-2 border-white/30 rounded shadow-sm p-4 mb-4">
                <div class="text-sm text-blue-100 mb-1">Your Return</div>
                <div class="text-3xl font-bold ${actual.return_pct >= 0 ? 'text-green-300' : 'text-red-300'}">
                    ${actual.return_pct >= 0 ? '+' : ''}${actual.return_pct.toFixed(2)}%
                </div>
            </div>

            ${spy ? `
            <div class="bg-white/10 backdrop-blur-sm border-2 border-white/30 rounded shadow-sm p-3 mb-3">
                <div class="text-xs text-blue-100 mb-1">S&P 500 Return</div>
                <div class="flex justify-between items-center">
                    <span class="font-semibold">SPY</span>
                    <span class="text-lg ${spy.return_pct >= 0 ? 'text-green-300' : 'text-red-300'}">
                        ${spy.return_pct >= 0 ? '+' : ''}${spy.return_pct.toFixed(2)}%
                    </span>
                </div>
            </div>
            ` : ''}

            <div class="grid grid-cols-2 gap-3 mb-4">
                <div class="bg-white/10 backdrop-blur-sm border-2 border-white/30 rounded shadow-sm p-3">
                    <div class="text-xs text-blue-100 mb-1">Best Benchmark</div>
                    <div class="font-semibold">${escapeHtml(best.ticker)}</div>
                    <div class="text-sm ${best.return_pct >= 0 ? 'text-green-300' : 'text-red-300'}">
                        ${best.return_pct >= 0 ? '+' : ''}${best.return_pct.toFixed(2)}%
                    </div>
                </div>

                <div class="bg-white/10 backdrop-blur-sm border-2 border-white/30 rounded shadow-sm p-3">
                    <div class="text-xs text-blue-100 mb-1">Worst Benchmark</div>
                    <div class="font-semibold">${escapeHtml(worst.ticker)}</div>
                    <div class="text-sm ${worst.return_pct >= 0 ? 'text-green-300' : 'text-red-300'}">
                        ${worst.return_pct >= 0 ? '+' : ''}${worst.return_pct.toFixed(2)}%
                    </div>
                </div>
            </div>

            <div class="bg-white/10 backdrop-blur-sm border-2 border-white/30 rounded shadow-sm p-3">
                <div class="text-xs text-blue-100 mb-1">Opportunity Cost</div>
                <div class="text-xl font-bold ${opportunityCost > 0 ? 'text-red-300' : 'text-green-300'}">
                    ${opportunityCost > 0 ? '-' : '+'}${formatCurrency(Math.abs(opportunityCost))}
                </div>
                <div class="text-xs text-blue-100 mt-1">
                    ${opportunityCost > 0 ? `vs ${escapeHtml(best.ticker)}` : 'Beating all benchmarks!'}
                </div>
            </div>

            <div class="mt-4 pt-4 border-t border-white/20 text-xs text-blue-100 text-center">
                Track your portfolio at Honest Portfolio
            </div>
        </div>
    `;
}

// ==================== PDF Upload ====================

async function fetchPdfUploadQuota() {
    if (!authManager.isAuthenticated()) {
        pdfUploadQuota = null;
        updatePdfQuotaUI();
        return;
    }

    try {
        const response = await authManager.authFetch(`${API_BASE}/uploads/pdf/quota`);
        if (response.ok) {
            pdfUploadQuota = await response.json();
        } else {
            pdfUploadQuota = null;
        }
    } catch (error) {
        console.error('Error fetching PDF quota:', error);
        pdfUploadQuota = null;
    }

    updatePdfQuotaUI();
}

function updatePdfQuotaUI() {
    const display = document.getElementById('pdf-quota-display');
    const dropZone = document.getElementById('pdf-drop-zone');
    const fileInput = document.getElementById('pdf-file-input');

    if (!display) return;

    if (!authManager.isAuthenticated() || !pdfUploadQuota) {
        display.classList.add('hidden');
        return;
    }

    display.classList.remove('hidden');

    const { remaining, limit } = pdfUploadQuota;
    const quotaText = display.querySelector('.quota-text');

    if (remaining === 0) {
        // Exhausted - disable upload
        quotaText.textContent = `Daily limit reached (${limit}/${limit})`;
        display.classList.remove('text-gray-600');
        display.classList.add('text-red-600');

        if (dropZone) {
            dropZone.classList.add('opacity-50', 'pointer-events-none');
        }
        if (fileInput) {
            fileInput.disabled = true;
        }
    } else {
        // Has remaining uploads
        quotaText.textContent = `${remaining} of ${limit} uploads remaining today`;
        display.classList.remove('text-red-600');
        display.classList.add('text-gray-600');

        if (dropZone) {
            dropZone.classList.remove('opacity-50', 'pointer-events-none');
        }
        if (fileInput) {
            fileInput.disabled = false;
        }
    }
}

function initPdfUpload() {
    const fileInput = document.getElementById('pdf-file-input');
    const dropZone = document.getElementById('pdf-drop-zone');

    // File input change handler
    if (fileInput) {
        fileInput.addEventListener('change', (e) => {
            if (e.target.files[0]) handlePdfFile(e.target.files[0]);
        });
    }

    // Drag and drop handlers
    if (dropZone) {
        dropZone.addEventListener('dragover', (e) => {
            e.preventDefault();
            dropZone.classList.add('border-[var(--primary)]', 'bg-[var(--primary)]/10');
        });

        dropZone.addEventListener('dragleave', (e) => {
            e.preventDefault();
            dropZone.classList.remove('border-[var(--primary)]', 'bg-[var(--primary)]/10');
        });

        dropZone.addEventListener('drop', (e) => {
            e.preventDefault();
            dropZone.classList.remove('border-[var(--primary)]', 'bg-[var(--primary)]/10');
            const file = e.dataTransfer.files[0];
            if (file && file.type === 'application/pdf') {
                handlePdfFile(file);
            } else {
                showPdfStatus('Please upload a PDF file', 'error');
            }
        });
    }

    // Modal event listeners
    initPdfModalListeners();
}

function initPdfModalListeners() {
    const backdrop = document.getElementById('pdf-modal-backdrop');
    const closeBtn = document.getElementById('pdf-modal-close');
    const cancelBtn = document.getElementById('pdf-cancel-btn');
    const saveBtn = document.getElementById('pdf-save-btn');
    const selectAll = document.getElementById('pdf-select-all');

    if (backdrop) backdrop.addEventListener('click', closePdfModal);
    if (closeBtn) closeBtn.addEventListener('click', closePdfModal);
    if (cancelBtn) cancelBtn.addEventListener('click', closePdfModal);
    if (saveBtn) saveBtn.addEventListener('click', saveSelectedTrades);

    // Select all checkbox
    if (selectAll) {
        selectAll.addEventListener('change', (e) => {
            const checkboxes = document.querySelectorAll('#pdf-trades-tbody input[type="checkbox"]:not(:disabled)');
            checkboxes.forEach(cb => {
                cb.checked = e.target.checked;
                const tradeId = cb.dataset.tradeId;
                if (e.target.checked) {
                    selectedTradeIds.add(tradeId);
                } else {
                    selectedTradeIds.delete(tradeId);
                }
            });
            updateSelectedCount();
        });
    }
}

async function handlePdfFile(file) {
    // Check auth
    if (!authManager.isAuthenticated()) {
        showPdfStatus('Please sign in to upload PDF trades', 'error');
        return;
    }

    // Check quota before attempting upload
    if (pdfUploadQuota && pdfUploadQuota.remaining <= 0) {
        showPdfStatus('Daily upload limit reached. Try again tomorrow.', 'error');
        return;
    }

    // Validate file
    if (file.type !== 'application/pdf') {
        showPdfStatus('Please upload a PDF file', 'error');
        return;
    }

    if (file.size > 10 * 1024 * 1024) {
        showPdfStatus('File too large. Maximum size is 10MB', 'error');
        return;
    }

    // Show loading
    showPdfStatus('Extracting trades from PDF... This may take a moment.', 'loading');

    try {
        const formData = new FormData();
        formData.append('file', file);

        // Note: Don't set Content-Type header for FormData - browser sets it with boundary
        const response = await fetch(`${API_BASE}/uploads/pdf/extract`, {
            method: 'POST',
            body: formData,
            credentials: 'include',
            headers: {
                'X-CSRFToken': authManager.csrfToken
            }
        });

        const result = await response.json();

        if (!response.ok) {
            if (response.status === 429) {
                await fetchPdfUploadQuota();  // Refresh quota
                throw new Error(result.error || 'Daily upload limit reached');
            }
            throw new Error(result.error || 'Failed to extract trades');
        }

        if (!result.trades || result.trades.length === 0) {
            showPdfStatus('No trades found in the PDF. Try a different document.', 'warning');
            return;
        }

        // Store trades and open modal
        extractedTrades = result.trades;
        selectedTradeIds = new Set(
            extractedTrades
                .filter(t => t.validation && t.validation.valid)
                .map(t => t.id)
        );

        showPdfStatus(`Found ${result.trades.length} trade(s). Review and confirm below.`, 'success');
        openPdfConfirmModal(result);

        // Refresh quota after successful upload
        await fetchPdfUploadQuota();

    } catch (error) {
        console.error('PDF upload error:', error);
        showPdfStatus(error.message || 'Failed to process PDF', 'error');
        // Refresh quota after error (in case it was a 429)
        await fetchPdfUploadQuota();
    }

    // Reset file input
    document.getElementById('pdf-file-input').value = '';
}

function showPdfStatus(message, type) {
    const statusDiv = document.getElementById('pdf-upload-status');
    if (!statusDiv) return;

    statusDiv.classList.remove('hidden');

    const styles = {
        loading: 'bg-blue-50 border-blue-200 text-blue-700',
        success: 'bg-green-50 border-green-200 text-green-700',
        error: 'bg-red-50 border-red-200 text-red-700',
        warning: 'bg-yellow-50 border-yellow-200 text-yellow-700'
    };

    // Remove all style classes
    statusDiv.className = 'mt-4 p-3 rounded border-2 ' + (styles[type] || styles.warning);

    if (type === 'loading') {
        statusDiv.innerHTML = `
            <div class="flex items-center gap-2">
                <svg class="animate-spin w-5 h-5" fill="none" viewBox="0 0 24 24">
                    <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                    <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                <span>${escapeHtml(message)}</span>
            </div>`;
    } else {
        statusDiv.textContent = message;
    }
}

function openPdfConfirmModal(result) {
    const modal = document.getElementById('pdf-confirm-modal');
    const notesDiv = document.getElementById('pdf-extraction-notes');
    const tbody = document.getElementById('pdf-trades-tbody');
    const selectAll = document.getElementById('pdf-select-all');

    // Show notes if any
    if (result.notes && result.notes.length > 0) {
        notesDiv.classList.remove('hidden');
        notesDiv.innerHTML = '<strong>Notes:</strong> ' + result.notes.map(n => escapeHtml(n)).join('; ');
    } else {
        notesDiv.classList.add('hidden');
    }

    // Render trades
    tbody.innerHTML = extractedTrades.map(trade => renderTradeRow(trade)).join('');

    // Add event listeners for checkboxes and inputs
    tbody.querySelectorAll('input[type="checkbox"]').forEach(cb => {
        cb.addEventListener('change', (e) => {
            const tradeId = e.target.dataset.tradeId;
            if (e.target.checked) {
                selectedTradeIds.add(tradeId);
            } else {
                selectedTradeIds.delete(tradeId);
            }
            updateSelectedCount();
        });
    });

    // Add input listeners for live editing
    tbody.querySelectorAll('.trade-input').forEach(input => {
        input.addEventListener('input', (e) => {
            const tradeId = e.target.dataset.tradeId;
            const field = e.target.dataset.field;
            const trade = extractedTrades.find(t => t.id === tradeId);
            if (trade) {
                trade[field] = e.target.value;
                // Recalculate total
                if (field === 'quantity' || field === 'price_per_share') {
                    const qty = parseFloat(trade.quantity) || 0;
                    const price = parseFloat(trade.price_per_share) || 0;
                    trade.total_amount = (qty * price).toFixed(2);
                    const totalCell = tbody.querySelector(`[data-total-id="${tradeId}"]`);
                    if (totalCell) totalCell.textContent = formatCurrency(trade.total_amount);
                }
            }
        });
    });

    // Reset select all
    if (selectAll) selectAll.checked = false;

    updateSelectedCount();

    // Show modal
    modal.classList.remove('hidden');
    document.body.style.overflow = 'hidden';
}

function renderTradeRow(trade) {
    const isSelected = selectedTradeIds.has(trade.id);
    const validation = trade.validation || { valid: true, errors: [], warnings: [] };
    const hasErrors = validation.errors && validation.errors.length > 0;
    const hasWarnings = validation.warnings && validation.warnings.length > 0;

    let statusIcon, statusClass, statusTitle;
    if (hasErrors) {
        statusIcon = '&#10060;'; // X
        statusClass = 'text-red-600';
        statusTitle = validation.errors.join(', ');
    } else if (hasWarnings) {
        statusIcon = '&#9888;'; // Warning
        statusClass = 'text-yellow-600';
        statusTitle = validation.warnings.join(', ');
    } else {
        statusIcon = '&#10003;'; // Check
        statusClass = 'text-green-600';
        statusTitle = 'Valid';
    }

    return `
        <tr class="${hasErrors ? 'bg-red-50' : 'hover:bg-gray-50'}">
            <td class="px-3 py-2">
                <input type="checkbox"
                       data-trade-id="${trade.id}"
                       ${isSelected && !hasErrors ? 'checked' : ''}
                       ${hasErrors ? 'disabled title="Cannot save - has errors"' : ''}
                       class="w-4 h-4">
            </td>
            <td class="px-3 py-2">
                <input type="text"
                       class="trade-input w-20 px-2 py-1 border rounded text-sm uppercase"
                       data-trade-id="${trade.id}"
                       data-field="ticker"
                       value="${escapeHtml(trade.ticker || '')}">
            </td>
            <td class="px-3 py-2">
                <input type="date"
                       class="trade-input px-2 py-1 border rounded text-sm"
                       data-trade-id="${trade.id}"
                       data-field="purchase_date"
                       value="${trade.purchase_date || ''}">
            </td>
            <td class="px-3 py-2 text-right">
                <input type="number"
                       class="trade-input w-24 px-2 py-1 border rounded text-sm text-right"
                       data-trade-id="${trade.id}"
                       data-field="quantity"
                       value="${trade.quantity || ''}"
                       step="0.0001" min="0">
            </td>
            <td class="px-3 py-2 text-right">
                <input type="number"
                       class="trade-input w-24 px-2 py-1 border rounded text-sm text-right"
                       data-trade-id="${trade.id}"
                       data-field="price_per_share"
                       value="${trade.price_per_share || ''}"
                       step="0.01" min="0">
            </td>
            <td class="px-3 py-2 text-right font-medium" data-total-id="${trade.id}">
                ${formatCurrency(trade.total_amount || 0)}
            </td>
            <td class="px-3 py-2 text-center ${statusClass}" title="${escapeHtml(statusTitle)}">
                ${statusIcon}
            </td>
        </tr>
    `;
}

function closePdfModal() {
    const modal = document.getElementById('pdf-confirm-modal');
    modal.classList.add('hidden');
    document.body.style.overflow = '';
}

function updateSelectedCount() {
    const selectedSpan = document.getElementById('pdf-selected-count');
    const totalSpan = document.getElementById('pdf-total-count');
    const saveBtn = document.getElementById('pdf-save-btn');

    if (selectedSpan) selectedSpan.textContent = selectedTradeIds.size;
    if (totalSpan) totalSpan.textContent = extractedTrades.length;
    if (saveBtn) saveBtn.disabled = selectedTradeIds.size === 0;
}

async function saveSelectedTrades() {
    const saveBtn = document.getElementById('pdf-save-btn');
    const originalText = saveBtn.textContent;
    saveBtn.disabled = true;
    saveBtn.textContent = 'Saving...';

    try {
        const tradesToSave = extractedTrades
            .filter(t => selectedTradeIds.has(t.id) && t.validation && t.validation.valid)
            .map(t => ({
                ticker: t.ticker,
                purchase_date: t.purchase_date,
                quantity: parseFloat(t.quantity),
                price_per_share: parseFloat(t.price_per_share)
            }));

        const response = await authManager.authFetch(`${API_BASE}/uploads/pdf/confirm`, {
            method: 'POST',
            body: JSON.stringify({ trades: tradesToSave })
        });

        const result = await response.json();

        if (!response.ok && response.status !== 207) {
            throw new Error(result.error || 'Failed to save trades');
        }

        closePdfModal();

        // Show result
        if (result.errors && result.errors.length > 0) {
            showSuccess(`Saved ${result.saved} of ${result.total} trades. Some had errors.`);
        } else {
            showSuccess(`Successfully saved ${result.saved} trade(s)`);
        }

        // Reload data
        await loadData();

    } catch (error) {
        console.error('Save trades error:', error);
        showError(error.message || 'Failed to save trades');
    } finally {
        saveBtn.disabled = false;
        saveBtn.textContent = originalText;
    }
}
