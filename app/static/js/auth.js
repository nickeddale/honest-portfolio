// Authentication Manager for Honest Portfolio
class AuthManager {
    constructor() {
        this.currentUser = null;
        this.listeners = [];
        this.csrfToken = null;
    }

    /**
     * Initialize the auth manager - check if user is logged in
     */
    async init() {
        await this.refreshCurrentUser();
        await this.fetchCsrfToken();
    }

    /**
     * Refresh current user from server
     */
    async refreshCurrentUser() {
        try {
            const response = await fetch('/api/auth/me', {
                credentials: 'include'
            });

            if (response.ok) {
                this.currentUser = await response.json();
                this._notifyListeners();
                return this.currentUser;
            } else {
                this.currentUser = null;
                this._notifyListeners();
                return null;
            }
        } catch (error) {
            console.error('Error fetching current user:', error);
            this.currentUser = null;
            this._notifyListeners();
            return null;
        }
    }

    /**
     * Fetch CSRF token from server
     */
    async fetchCsrfToken() {
        try {
            const response = await fetch('/api/csrf-token', {
                credentials: 'include'
            });
            if (response.ok) {
                const data = await response.json();
                this.csrfToken = data.csrf_token;
            }
        } catch (error) {
            console.error('Error fetching CSRF token:', error);
        }
    }

    /**
     * Get current user
     */
    getCurrentUser() {
        return this.currentUser;
    }

    /**
     * Check if user is authenticated
     */
    isAuthenticated() {
        return this.currentUser !== null;
    }

    /**
     * Redirect to OAuth login
     * @param {string} provider - OAuth provider name (e.g., 'google')
     */
    loginWith(provider) {
        window.location.href = `/api/auth/${provider}/login`;
    }

    /**
     * Logout current user
     */
    async logout() {
        try {
            const response = await fetch('/api/auth/logout', {
                method: 'POST',
                credentials: 'include',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.csrfToken
                }
            });

            if (response.ok) {
                this.currentUser = null;
                this.csrfToken = null;
                this._notifyListeners();
                window.location.href = '/login.html';
            }
        } catch (error) {
            console.error('Logout error:', error);
        }
    }

    /**
     * Check if dev mode is enabled
     */
    async checkDevMode() {
        try {
            const response = await fetch('/api/auth/dev-status', {
                credentials: 'include'
            });
            if (response.ok) {
                const data = await response.json();
                return data.dev_mode;
            }
            return false;
        } catch (error) {
            console.error('Error checking dev mode:', error);
            return false;
        }
    }

    /**
     * Login as test user (dev mode only)
     */
    async devLogin() {
        try {
            const response = await fetch('/api/test/auth/create-test-user', {
                method: 'POST',
                credentials: 'include',
                headers: {
                    'Content-Type': 'application/json'
                }
            });

            if (response.ok) {
                const data = await response.json();
                this.currentUser = data.user;
                await this.fetchCsrfToken();
                this._notifyListeners();
                window.location.href = '/';
                return true;
            } else {
                const error = await response.json();
                console.error('Dev login failed:', error);
                return false;
            }
        } catch (error) {
            console.error('Dev login error:', error);
            return false;
        }
    }

    /**
     * Subscribe to auth state changes
     * @param {Function} callback - Function to call when auth state changes
     * @returns {Function} Unsubscribe function
     */
    onAuthStateChanged(callback) {
        this.listeners.push(callback);
        // Call immediately with current state
        callback(this.currentUser);

        // Return unsubscribe function
        return () => {
            this.listeners = this.listeners.filter(l => l !== callback);
        };
    }

    /**
     * Notify all listeners of auth state change
     */
    _notifyListeners() {
        this.listeners.forEach(listener => {
            try {
                listener(this.currentUser);
            } catch (error) {
                console.error('Error in auth listener:', error);
            }
        });
    }

    /**
     * Get headers for authenticated API requests
     */
    getAuthHeaders() {
        const headers = {
            'Content-Type': 'application/json'
        };
        if (this.csrfToken) {
            headers['X-CSRFToken'] = this.csrfToken;
        }
        return headers;
    }

    /**
     * Make an authenticated fetch request
     * @param {string} url - URL to fetch
     * @param {Object} options - Fetch options
     */
    async authFetch(url, options = {}) {
        const defaultOptions = {
            credentials: 'include',
            headers: this.getAuthHeaders()
        };

        const mergedOptions = {
            ...defaultOptions,
            ...options,
            headers: {
                ...defaultOptions.headers,
                ...(options.headers || {})
            }
        };

        const response = await fetch(url, mergedOptions);

        // Handle 401 Unauthorized - redirect to login
        if (response.status === 401) {
            this.currentUser = null;
            this._notifyListeners();
            window.location.href = '/login.html';
            throw new Error('Unauthorized');
        }

        return response;
    }
}

// Create global auth manager instance
const authManager = new AuthManager();
