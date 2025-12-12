// Guest Mode Manager - handles localStorage persistence for non-authenticated users

const GUEST_STORAGE_KEY = 'honest_portfolio_guest_purchases';
const GUEST_PROMPT_DISMISSED_KEY = 'honest_portfolio_prompt_dismissed';
const GUEST_PROMPT_COUNT_KEY = 'honest_portfolio_prompt_count';

class GuestManager {
    constructor() {
        this.purchases = this._loadFromStorage();
    }

    /**
     * Check if there are any guest purchases in localStorage
     */
    hasGuestPurchases() {
        return this.purchases.length > 0;
    }

    /**
     * Get all guest purchases
     */
    getGuestPurchases() {
        return [...this.purchases];
    }

    /**
     * Add a new guest purchase to localStorage
     * @param {Object} purchase - Purchase data (must include ticker, purchase_date, amount, shares_bought, price_at_purchase)
     */
    addGuestPurchase(purchase) {
        const newPurchase = {
            id: `guest_${Date.now()}`,
            ticker: purchase.ticker,
            purchase_date: purchase.purchase_date,
            amount: purchase.amount,
            shares_bought: purchase.shares_bought,
            price_at_purchase: purchase.price_at_purchase,
            entry_mode: purchase.entry_mode || 'quick',
            created_at: new Date().toISOString()
        };

        this.purchases.push(newPurchase);
        this._saveToStorage();
        return newPurchase;
    }

    /**
     * Delete a guest purchase by ID
     * @param {string} id - The purchase ID (must start with "guest_")
     */
    deleteGuestPurchase(id) {
        if (!id.startsWith('guest_')) {
            console.warn('Attempted to delete non-guest purchase from localStorage');
            return false;
        }

        const initialLength = this.purchases.length;
        this.purchases = this.purchases.filter(p => p.id !== id);

        if (this.purchases.length < initialLength) {
            this._saveToStorage();
            return true;
        }
        return false;
    }

    /**
     * Clear all guest purchases (called after successful migration)
     */
    clearGuestPurchases() {
        this.purchases = [];
        this._saveToStorage();
    }

    /**
     * Check if signup prompt has been dismissed for this session
     */
    isPromptDismissed() {
        return sessionStorage.getItem(GUEST_PROMPT_DISMISSED_KEY) === 'true';
    }

    /**
     * Dismiss the signup prompt for this session
     */
    dismissPrompt() {
        sessionStorage.setItem(GUEST_PROMPT_DISMISSED_KEY, 'true');
    }

    /**
     * Get the number of times we've shown the prompt
     */
    getPromptCount() {
        return parseInt(localStorage.getItem(GUEST_PROMPT_COUNT_KEY) || '0', 10);
    }

    /**
     * Increment the prompt shown count
     */
    incrementPromptCount() {
        const count = this.getPromptCount() + 1;
        localStorage.setItem(GUEST_PROMPT_COUNT_KEY, count.toString());
        return count;
    }

    /**
     * Should we show the signup prompt?
     * Show after each purchase unless dismissed for this session
     */
    shouldShowPrompt() {
        return !this.isPromptDismissed();
    }

    /**
     * Load purchases from localStorage
     */
    _loadFromStorage() {
        try {
            const stored = localStorage.getItem(GUEST_STORAGE_KEY);
            if (stored) {
                return JSON.parse(stored);
            }
        } catch (e) {
            console.error('Error loading guest purchases from localStorage:', e);
        }
        return [];
    }

    /**
     * Save purchases to localStorage
     */
    _saveToStorage() {
        try {
            localStorage.setItem(GUEST_STORAGE_KEY, JSON.stringify(this.purchases));
        } catch (e) {
            console.error('Error saving guest purchases to localStorage:', e);
            // Handle quota exceeded
            if (e.name === 'QuotaExceededError') {
                alert('Storage limit reached. Please sign up to save your data to the cloud.');
            }
        }
    }
}

// Create global instance
const guestManager = new GuestManager();
