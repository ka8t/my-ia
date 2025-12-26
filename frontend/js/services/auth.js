/**
 * Service d'authentification
 * Gère le login, logout et la persistence du token JWT
 */

const AuthService = {
    TOKEN_KEY: 'access_token',
    USER_KEY: 'user_data',
    _refreshTimer: null,
    _lastActivity: Date.now(),
    REFRESH_MARGIN_MS: 5 * 60 * 1000, // Refresh 5 min avant expiration
    INACTIVITY_TIMEOUT_MS: 30 * 60 * 1000, // Deconnexion apres 30 min d'inactivite

    /**
     * Authentifie l'utilisateur avec email/password
     * @param {string} email
     * @param {string} password
     * @returns {Promise<{success: boolean, error?: string}>}
     */
    async login(email, password) {
        try {
            const response = await fetch(`${this.getApiUrl()}/auth/jwt/login`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
                body: new URLSearchParams({
                    username: email,
                    password: password
                })
            });

            if (!response.ok) {
                const error = await response.json();
                if (error.detail === 'LOGIN_BAD_CREDENTIALS') {
                    return { success: false, error: 'Email ou mot de passe incorrect' };
                }
                if (error.detail === 'LOGIN_USER_NOT_VERIFIED') {
                    return { success: false, error: 'Compte non verifie. Verifiez votre email.' };
                }
                return { success: false, error: error.detail || 'Erreur de connexion' };
            }

            const data = await response.json();
            this.setToken(data.access_token);

            // Charger les infos utilisateur
            await this.loadUserInfo();

            return { success: true };
        } catch (error) {
            console.error('Login error:', error);
            return { success: false, error: 'Impossible de se connecter au serveur' };
        }
    },

    /**
     * Inscription d'un nouvel utilisateur
     * @param {string} email
     * @param {string} password
     * @param {string} username
     * @returns {Promise<{success: boolean, error?: string}>}
     */
    async register(email, password, username) {
        try {
            const response = await fetch(`${this.getApiUrl()}/auth/register/register`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    email: email,
                    password: password,
                    username: username
                })
            });

            if (!response.ok) {
                const error = await response.json();
                if (error.detail === 'REGISTER_USER_ALREADY_EXISTS') {
                    return { success: false, error: 'Cet email est deja utilise' };
                }
                return { success: false, error: error.detail || 'Erreur lors de l\'inscription' };
            }

            return { success: true };
        } catch (error) {
            console.error('Register error:', error);
            return { success: false, error: 'Impossible de se connecter au serveur' };
        }
    },

    /**
     * Deconnecte l'utilisateur
     */
    logout() {
        localStorage.removeItem(this.TOKEN_KEY);
        localStorage.removeItem(this.USER_KEY);
        // Recharger la page pour afficher le login
        window.location.reload();
    },

    /**
     * Verifie si l'utilisateur est authentifie
     * @returns {boolean}
     */
    isAuthenticated() {
        const token = this.getToken();
        if (!token) return false;

        // Verifier si le token n'est pas expire
        try {
            const payload = JSON.parse(atob(token.split('.')[1]));
            const expiry = payload.exp * 1000; // Convert to milliseconds
            return Date.now() < expiry;
        } catch {
            return false;
        }
    },

    /**
     * Recupere le token JWT
     * @returns {string|null}
     */
    getToken() {
        return localStorage.getItem(this.TOKEN_KEY);
    },

    /**
     * Stocke le token JWT
     * @param {string} token
     */
    setToken(token) {
        localStorage.setItem(this.TOKEN_KEY, token);
    },

    /**
     * Recupere les donnees utilisateur
     * @returns {object|null}
     */
    getUser() {
        const userData = localStorage.getItem(this.USER_KEY);
        return userData ? JSON.parse(userData) : null;
    },

    /**
     * Charge les informations utilisateur depuis l'API
     */
    async loadUserInfo() {
        try {
            const response = await fetch(`${this.getApiUrl()}/me`, {
                headers: {
                    'Authorization': `Bearer ${this.getToken()}`
                }
            });

            if (response.ok) {
                const user = await response.json();
                localStorage.setItem(this.USER_KEY, JSON.stringify(user));
                return user;
            }
        } catch (error) {
            console.error('Error loading user info:', error);
        }
        return null;
    },

    /**
     * Recupere l'URL de l'API
     * @returns {string}
     */
    getApiUrl() {
        const ENV = window.ENV_CONFIG || {};
        return localStorage.getItem('apiUrl') || ENV.apiUrl || 'http://localhost:8080';
    },

    /**
     * Retourne les headers d'authentification
     * @returns {object}
     */
    getAuthHeaders() {
        const token = this.getToken();
        return token ? { 'Authorization': `Bearer ${token}` } : {};
    },

    /**
     * Retourne le temps restant avant expiration du token (en ms)
     * @returns {number}
     */
    getTokenTimeRemaining() {
        const token = this.getToken();
        if (!token) return 0;

        try {
            const payload = JSON.parse(atob(token.split('.')[1]));
            const expiry = payload.exp * 1000;
            return Math.max(0, expiry - Date.now());
        } catch {
            return 0;
        }
    },

    /**
     * Refresh le token JWT
     * @returns {Promise<boolean>}
     */
    async refreshToken() {
        try {
            const response = await fetch(`${this.getApiUrl()}/auth/refresh`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${this.getToken()}`
                }
            });

            if (response.ok) {
                const data = await response.json();
                this.setToken(data.access_token);
                console.log('[Auth] Token refreshed successfully');
                return true;
            }

            console.warn('[Auth] Token refresh failed:', response.status);
            return false;
        } catch (error) {
            console.error('[Auth] Token refresh error:', error);
            return false;
        }
    },

    /**
     * Met a jour le timestamp de derniere activite
     */
    updateActivity() {
        this._lastActivity = Date.now();
    },

    /**
     * Verifie si l'utilisateur est actif
     * @returns {boolean}
     */
    isUserActive() {
        return (Date.now() - this._lastActivity) < this.INACTIVITY_TIMEOUT_MS;
    },

    /**
     * Demarre le refresh automatique du token
     */
    startAutoRefresh() {
        // Arreter le timer existant
        this.stopAutoRefresh();

        // Verifier toutes les minutes
        this._refreshTimer = setInterval(async () => {
            // Ne pas refresh si l'utilisateur est inactif
            if (!this.isUserActive()) {
                console.log('[Auth] User inactive, skipping refresh');
                return;
            }

            const timeRemaining = this.getTokenTimeRemaining();

            // Si moins de 5 minutes avant expiration, refresh
            if (timeRemaining > 0 && timeRemaining < this.REFRESH_MARGIN_MS) {
                console.log('[Auth] Token expiring soon, refreshing...');
                const success = await this.refreshToken();
                if (!success && timeRemaining < 60000) {
                    // Si refresh echoue et moins d'1 minute, logout
                    console.warn('[Auth] Token expired, logging out');
                    this.logout();
                }
            }
        }, 60000); // Check toutes les 60 secondes

        // Ajouter les listeners d'activite
        ['click', 'keypress', 'scroll', 'mousemove'].forEach(event => {
            document.addEventListener(event, () => this.updateActivity(), { passive: true });
        });

        console.log('[Auth] Auto-refresh started');
    },

    /**
     * Arrete le refresh automatique
     */
    stopAutoRefresh() {
        if (this._refreshTimer) {
            clearInterval(this._refreshTimer);
            this._refreshTimer = null;
        }
    }
};

// Export pour utilisation globale
window.AuthService = AuthService;
