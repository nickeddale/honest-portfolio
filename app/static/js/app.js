// Honest Portfolio - Main Application
const API_BASE = '/api';

// State
let purchases = [];
let portfolioSummary = null;
let portfolioHistory = null;
let chart = null;

// Router state
let currentView = 'portfolio'; // 'portfolio' | 'purchase-detail'
let currentPurchaseId = null;
let purchaseDetail = null;
let detailChart = null;

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
const panelQuickAdd = document.getElementById('panel-quick-add');
const panelDetailedEntry = document.getElementById('panel-detailed-entry');

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
    if (tab === 'quick-add') {
        // Update tab styles
        tabQuickAdd.classList.add('text-blue-600', 'border-blue-600');
        tabQuickAdd.classList.remove('text-gray-500', 'border-transparent');
        tabDetailedEntry.classList.remove('text-blue-600', 'border-blue-600');
        tabDetailedEntry.classList.add('text-gray-500', 'border-transparent');

        // Show/hide panels
        panelQuickAdd.classList.remove('hidden');
        panelDetailedEntry.classList.add('hidden');
    } else {
        // Update tab styles
        tabDetailedEntry.classList.add('text-blue-600', 'border-blue-600');
        tabDetailedEntry.classList.remove('text-gray-500', 'border-transparent');
        tabQuickAdd.classList.remove('text-blue-600', 'border-blue-600');
        tabQuickAdd.classList.add('text-gray-500', 'border-transparent');

        // Show/hide panels
        panelDetailedEntry.classList.remove('hidden');
        panelQuickAdd.classList.add('hidden');
    }
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

    if (!authManager.isAuthenticated()) {
        window.location.href = '/login.html';
        return;
    }

    // Update user UI
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

    // Setup auto-calculation for detailed entry
    setupDetailedEntryCalculation();

    // Initialize router
    initRouter();

    // Initialize modal event listeners
    initModalListeners();

    // Register service worker
    if ('serviceWorker' in navigator) {
        navigator.serviceWorker.register('/static/js/sw.js')
            .then(reg => console.log('Service Worker registered'))
            .catch(err => console.error('Service Worker registration failed:', err));
    }
}

function updateUserUI() {
    const user = authManager.getCurrentUser();
    if (!user) return;

    const userSection = document.getElementById('user-section');
    const userName = document.getElementById('user-name');
    const userInitials = document.getElementById('user-initials');
    const userPicture = document.getElementById('user-picture');

    if (userSection) {
        userSection.classList.remove('hidden');
    }

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
        await authManager.authFetch(`${API_BASE}/purchases/${id}`, { method: 'DELETE' });
        showToast('Purchase deleted successfully', 'success');
        await loadData();
    } catch (error) {
        showToast('Failed to delete purchase', 'error');
    }
}

function renderPurchasesList() {
    if (purchases.length === 0) {
        purchasesList.innerHTML = '<p class="text-gray-500">No purchases yet</p>';
        return;
    }

    purchasesList.innerHTML = purchases.map(p => `
        <div class="flex items-center justify-between p-3 bg-gray-50 rounded-lg cursor-pointer hover:bg-gray-100 transition-colors"
             onclick="navigateToPurchase(${p.id})">
            <div>
                <span class="font-semibold text-gray-800">${p.ticker}</span>
                <span class="text-gray-500 text-sm ml-2">${formatDate(p.purchase_date)}</span>
            </div>
            <div class="flex items-center gap-4">
                <span class="text-gray-800">${formatCurrency(p.amount)}</span>
                <span class="text-gray-500 text-sm">${p.shares_bought.toFixed(4)} shares @ ${formatCurrency(p.price_at_purchase)}</span>
                <button onclick="event.stopPropagation(); deletePurchase(${p.id})" class="text-red-500 hover:text-red-700">
                    <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                    </svg>
                </button>
                <svg class="w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
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
        `text-sm ${actual.gain_loss >= 0 ? 'text-green-600' : 'text-red-600'}`;

    // Best alternative
    if (alternatives.length > 0) {
        const best = alternatives.reduce((a, b) => a.current_value > b.current_value ? a : b);
        document.getElementById('best-alt-value').textContent = formatCurrency(best.current_value);
        document.getElementById('best-alt-name').textContent = `${best.name} (${best.ticker})`;

        // Opportunity cost
        const oppCost = best.current_value - actual.current_value;
        document.getElementById('opportunity-cost').textContent = formatCurrency(Math.abs(oppCost));
        document.getElementById('opportunity-cost').className =
            `text-2xl font-bold ${oppCost > 0 ? 'text-red-600' : 'text-green-600'}`;
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
        comparisonTbody.innerHTML = '<tr><td colspan="5" class="px-6 py-4 text-center text-gray-500">No purchases yet</td></tr>';
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
        <tr class="${row.isActual ? 'bg-blue-50' : ''} ${idx === 0 ? 'ring-2 ring-green-500' : ''}">
            <td class="px-6 py-4 whitespace-nowrap">
                <div class="flex items-center">
                    ${idx === 0 ? '<span class="text-green-500 mr-2">👑</span>' : ''}
                    <span class="font-medium ${row.isActual ? 'text-blue-700' : 'text-gray-900'}">${row.name || row.ticker}</span>
                    ${row.isActual ? '<span class="ml-2 px-2 py-1 text-xs bg-blue-200 text-blue-800 rounded">You</span>' : ''}
                </div>
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-right text-gray-500">${formatCurrency(row.total_invested)}</td>
            <td class="px-6 py-4 whitespace-nowrap text-right font-medium text-gray-900">${formatCurrency(row.current_value)}</td>
            <td class="px-6 py-4 whitespace-nowrap text-right ${row.gain_loss >= 0 ? 'text-green-600' : 'text-red-600'}">
                ${row.gain_loss >= 0 ? '+' : ''}${formatCurrency(row.gain_loss)}
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-right ${row.return_pct >= 0 ? 'text-green-600' : 'text-red-600'}">
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
    toast.className = `pointer-events-auto flex items-center gap-3 px-4 py-3 rounded-lg shadow-lg transform transition-all duration-300 translate-x-full opacity-0 max-w-sm`;

    // Type-specific styles
    const styles = {
        success: { bg: 'bg-green-50 border border-green-200', icon: 'text-green-500', iconPath: 'M5 13l4 4L19 7' },
        error: { bg: 'bg-red-50 border border-red-200', icon: 'text-red-500', iconPath: 'M6 18L18 6M6 6l12 12' },
        warning: { bg: 'bg-yellow-50 border border-yellow-200', icon: 'text-yellow-500', iconPath: 'M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z' },
        info: { bg: 'bg-blue-50 border border-blue-200', icon: 'text-blue-500', iconPath: 'M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z' }
    };

    const style = styles[type] || styles.info;
    toast.classList.add(...style.bg.split(' '));

    toast.innerHTML = `
        <svg class="w-5 h-5 flex-shrink-0 ${style.icon}" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="${style.iconPath}"/>
        </svg>
        <span class="text-sm font-medium text-gray-800 flex-1">${message}</span>
        <button class="text-gray-400 hover:text-gray-600 flex-shrink-0" onclick="this.parentElement.remove()">
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
            modalIcon.className = 'flex-shrink-0 w-10 h-10 rounded-full bg-red-100 flex items-center justify-center';
            modalIcon.innerHTML = `<svg class="w-6 h-6 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/>
            </svg>`;
            modalConfirm.className = 'px-4 py-2 text-sm font-medium text-white bg-red-600 hover:bg-red-700 rounded-md transition-colors';
        } else {
            modalIcon.className = 'flex-shrink-0 w-10 h-10 rounded-full bg-blue-100 flex items-center justify-center';
            modalIcon.innerHTML = `<svg class="w-6 h-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
            </svg>`;
            modalConfirm.className = 'px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-md transition-colors';
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

    const returnClass = actual.gain_loss >= 0 ? 'text-green-600' : 'text-red-600';
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
        const diffClass = diff > 0 ? 'text-red-600' : 'text-green-600';
        const borderClass = diff > 0 ? 'border-red-200 bg-red-50' : 'border-green-200 bg-green-50';
        const diffText = diff > 0
            ? `You missed out on ${formatCurrency(diff)}`
            : `You're ahead by ${formatCurrency(Math.abs(diff))}`;

        return `
            <div class="border rounded-lg p-4 ${borderClass}">
                <div class="flex justify-between items-start mb-2">
                    <div>
                        <span class="font-semibold text-gray-800">${alt.ticker}</span>
                        <span class="text-gray-500 text-sm block">${alt.name}</span>
                    </div>
                    <span class="text-lg font-bold ${alt.return_pct >= 0 ? 'text-green-600' : 'text-red-600'}">
                        ${alt.return_pct >= 0 ? '+' : ''}${alt.return_pct.toFixed(2)}%
                    </span>
                </div>
                <p class="text-gray-600 text-sm">
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
        <tr class="${row.isActual ? 'bg-blue-50' : ''} ${idx === 0 ? 'ring-2 ring-green-500' : ''}">
            <td class="px-6 py-4 whitespace-nowrap">
                <div class="flex items-center">
                    ${idx === 0 ? '<span class="text-green-500 mr-2">👑</span>' : ''}
                    <span class="font-medium ${row.isActual ? 'text-blue-700' : 'text-gray-900'}">${row.isActual ? row.name : row.name || row.ticker}</span>
                    ${row.isActual ? '<span class="ml-2 px-2 py-1 text-xs bg-blue-200 text-blue-800 rounded">You</span>' : ''}
                </div>
            </td>
            <td class="px-6 py-4 text-right text-gray-500">${formatCurrency(row.price_at_purchase)}</td>
            <td class="px-6 py-4 text-right text-gray-500">${row.shares.toFixed(4)}</td>
            <td class="px-6 py-4 text-right text-gray-500">${formatCurrency(row.current_price)}</td>
            <td class="px-6 py-4 text-right font-medium">${formatCurrency(row.current_value)}</td>
            <td class="px-6 py-4 text-right ${row.return_pct >= 0 ? 'text-green-600' : 'text-red-600'}">
                ${row.return_pct >= 0 ? '+' : ''}${row.return_pct.toFixed(2)}%
            </td>
            <td class="px-6 py-4 text-right ${row.difference > 0 ? 'text-red-600' : row.difference < 0 ? 'text-green-600' : 'text-gray-500'}">
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

        URL.revokeObjectURL(url);
        showToast('Image downloaded successfully', 'success');
    } catch (error) {
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
        <div class="bg-gradient-to-br from-blue-500 to-purple-600 p-6 rounded-lg shadow-lg text-white">
            <h3 class="text-2xl font-bold mb-4">My Portfolio Performance</h3>

            <div class="bg-white/10 backdrop-blur-sm rounded-lg p-4 mb-4">
                <div class="text-sm text-blue-100 mb-1">Your Return</div>
                <div class="text-3xl font-bold ${actual.return_pct >= 0 ? 'text-green-300' : 'text-red-300'}">
                    ${actual.return_pct >= 0 ? '+' : ''}${actual.return_pct.toFixed(2)}%
                </div>
            </div>

            <div class="grid grid-cols-2 gap-3 mb-4">
                <div class="bg-white/10 backdrop-blur-sm rounded-lg p-3">
                    <div class="text-xs text-blue-100 mb-1">Best Benchmark</div>
                    <div class="font-semibold">${best.ticker}</div>
                    <div class="text-sm ${best.return_pct >= 0 ? 'text-green-300' : 'text-red-300'}">
                        ${best.return_pct >= 0 ? '+' : ''}${best.return_pct.toFixed(2)}%
                    </div>
                </div>

                <div class="bg-white/10 backdrop-blur-sm rounded-lg p-3">
                    <div class="text-xs text-blue-100 mb-1">Worst Benchmark</div>
                    <div class="font-semibold">${worst.ticker}</div>
                    <div class="text-sm ${worst.return_pct >= 0 ? 'text-green-300' : 'text-red-300'}">
                        ${worst.return_pct >= 0 ? '+' : ''}${worst.return_pct.toFixed(2)}%
                    </div>
                </div>
            </div>

            <div class="bg-white/10 backdrop-blur-sm rounded-lg p-3">
                <div class="text-xs text-blue-100 mb-1">Opportunity Cost</div>
                <div class="text-xl font-bold ${opportunityCost > 0 ? 'text-red-300' : 'text-green-300'}">
                    ${opportunityCost > 0 ? '-' : '+'}${formatCurrency(Math.abs(opportunityCost))}
                </div>
                <div class="text-xs text-blue-100 mt-1">
                    ${opportunityCost > 0 ? `vs ${best.ticker}` : 'Beating all benchmarks!'}
                </div>
            </div>

            <div class="mt-4 pt-4 border-t border-white/20 text-xs text-blue-100 text-center">
                Track your portfolio at Honest Portfolio
            </div>
        </div>
    `;
}
