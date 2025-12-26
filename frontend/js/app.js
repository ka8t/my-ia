/**
 * MY-IA Frontend Application
 * Point d'entree principal - Version modulaire
 *
 * Dependencies (ordre de chargement dans index.html):
 * 1. Libs externes (marked, hljs)
 * 2. js/services/auth.js
 * 3. js/services/api.js
 * 4. js/utils/dom.js
 * 5. js/utils/format.js
 * 6. js/components/toast.js
 * 7. js/components/confirm.js
 * 8. js/components/markdown.js
 * 9. js/modules/settings.js
 * 10. js/modules/conversations.js
 * 11. js/modules/messages.js
 * 12. js/modules/streaming.js
 * 13. js/modules/upload.js
 * 14. js/app.js (ce fichier)
 */

// Mode debug (centralise dans config.js via window.DEBUG)

// Configuration globale
// Note: API_URL vient de ENV_CONFIG (genere par Docker depuis .env)
// TOP_K est gere par l'admin dans .env, pas modifiable par l'utilisateur
const ENV = window.ENV_CONFIG || {};
window.CONFIG = {
    apiUrl: ENV.apiUrl || 'http://localhost:8080',
    showSources: false,
    theme: localStorage.getItem('theme') || 'light',
    mode: 'chat',
    defaultModeId: 1
};

// Etat global
window.currentConversationId = null;
window.conversations = [];
window.isStreaming = false;
window.abortController = null;

// =============================================================================
// INITIALISATION
// =============================================================================

document.addEventListener('DOMContentLoaded', () => {
    initializeTheme();
    initializeLoginListeners();

    if (AuthService.isAuthenticated()) {
        showApp();
        initializeApp();
    } else {
        showLogin();
    }
});

/**
 * Initialise l'application apres authentification
 */
async function initializeApp() {
    try {
        AuthService.startAutoRefresh();
        await loadPreferences();
        initializeEventListeners();
        await loadConversationsFromBackend();
        displayUserInfo();

        if (window.DEBUG) {
            const remaining = Math.round(AuthService.getTokenTimeRemaining() / 60000);
            console.log(`[App] Token expires in ${remaining} minutes`);
        }
    } catch (error) {
        console.error('Error initializing app:', error);
    }
}

/**
 * Affiche l'ecran de login
 */
function showLogin() {
    document.getElementById('loginScreen').style.display = 'flex';
    document.getElementById('appContainer').style.display = 'none';
}

/**
 * Affiche l'application principale
 */
function showApp() {
    document.getElementById('loginScreen').style.display = 'none';
    document.getElementById('appContainer').style.display = 'flex';
}

// =============================================================================
// AUTHENTIFICATION
// =============================================================================

/**
 * Initialise les event listeners de login/register
 */
function initializeLoginListeners() {
    // Login
    document.getElementById('loginForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        const email = document.getElementById('loginEmail').value;
        const password = document.getElementById('loginPassword').value;
        const errorDiv = document.getElementById('loginError');
        const btn = document.getElementById('loginBtn');

        btn.disabled = true;
        btn.textContent = 'Connexion...';
        errorDiv.style.display = 'none';

        const result = await AuthService.login(email, password);

        if (result.success) {
            showApp();
            initializeApp();
        } else {
            errorDiv.textContent = result.error;
            errorDiv.style.display = 'block';
        }

        btn.disabled = false;
        btn.textContent = 'Se connecter';
    });

    // Afficher formulaire inscription
    document.getElementById('showRegisterBtn').addEventListener('click', () => {
        document.getElementById('loginForm').style.display = 'none';
        document.querySelector('.login-separator').style.display = 'none';
        document.getElementById('showRegisterBtn').style.display = 'none';
        document.getElementById('registerForm').style.display = 'flex';
    });

    // Retour au login
    document.getElementById('backToLoginBtn').addEventListener('click', () => {
        document.getElementById('registerForm').style.display = 'none';
        document.getElementById('loginForm').style.display = 'flex';
        document.querySelector('.login-separator').style.display = 'flex';
        document.getElementById('showRegisterBtn').style.display = 'block';
    });

    // Register
    document.getElementById('registerForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        const email = document.getElementById('registerEmail').value;
        const username = document.getElementById('registerUsername').value;
        const password = document.getElementById('registerPassword').value;
        const errorDiv = document.getElementById('registerError');
        const btn = e.target.querySelector('.btn-login');

        btn.disabled = true;
        btn.textContent = 'Inscription...';
        errorDiv.style.display = 'none';

        const result = await AuthService.register(email, password, username);

        if (result.success) {
            const loginResult = await AuthService.login(email, password);
            if (loginResult.success) {
                showApp();
                initializeApp();
            } else {
                showToast('Compte cree ! Vous pouvez maintenant vous connecter.', 'success');
                document.getElementById('backToLoginBtn').click();
            }
        } else {
            errorDiv.textContent = result.error;
            errorDiv.style.display = 'block';
        }

        btn.disabled = false;
        btn.textContent = 'S\'inscrire';
    });
}

// =============================================================================
// EVENT LISTENERS
// =============================================================================

/**
 * Initialise tous les event listeners de l'application
 */
function initializeEventListeners() {
    // Sidebar toggle
    document.getElementById('toggleSidebar').addEventListener('click', () => {
        document.getElementById('sidebar').classList.toggle('hidden');
    });

    // Nouvelle conversation
    document.getElementById('newChatBtn').addEventListener('click', createNewConversation);

    // Theme
    document.getElementById('themeToggle').addEventListener('click', toggleTheme);

    // Logout
    document.getElementById('logoutBtn').addEventListener('click', async () => {
        const confirmed = await showConfirm({
            title: 'Deconnexion',
            message: 'Voulez-vous vraiment vous deconnecter ?',
            confirmText: 'Se deconnecter',
            cancelText: 'Annuler',
            type: 'warning'
        });
        if (confirmed) {
            AuthService.logout();
        }
    });

    // Parametres
    document.getElementById('settingsBtn').addEventListener('click', () => {
        loadSettings();
        document.getElementById('settingsPanel').classList.add('open');
        document.getElementById('settingsPanel').style.display = 'block';
    });

    document.getElementById('closeSettings').addEventListener('click', () => {
        document.getElementById('settingsPanel').classList.remove('open');
        setTimeout(() => {
            document.getElementById('settingsPanel').style.display = 'none';
        }, 300);
    });

    document.getElementById('saveSettings').addEventListener('click', saveSettings);

    // Mode toggle
    document.getElementById('modeToggle').addEventListener('change', (e) => {
        window.CONFIG.mode = e.target.checked ? 'assistant' : 'chat';
        document.getElementById('chatMode').textContent = e.target.checked ? 'Assistant' : 'ChatBot';
    });

    // Formulaire de chat
    const chatForm = document.getElementById('chatForm');
    const messageInput = document.getElementById('messageInput');

    chatForm.addEventListener('submit', (e) => {
        e.preventDefault();
        sendMessage();
    });

    // Auto-resize textarea
    messageInput.addEventListener('input', (e) => {
        e.target.style.height = 'auto';
        e.target.style.height = e.target.scrollHeight + 'px';
        document.getElementById('charCount').textContent = `${e.target.value.length} caracteres`;
    });

    // Enter pour envoyer (sans Shift)
    messageInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    // Suggestions
    document.querySelectorAll('.suggestion-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            messageInput.value = btn.dataset.query;
            sendMessage();
        });
    });

    // Stop generation
    document.getElementById('stopBtn').addEventListener('click', stopGeneration);

    // Aide modes
    const modeHelpBtn = document.getElementById('modeHelpBtn');
    const modeHelpTooltip = document.getElementById('modeHelpTooltip');

    modeHelpBtn.addEventListener('click', (e) => {
        e.preventDefault();
        e.stopPropagation();
        modeHelpTooltip.style.display = modeHelpTooltip.style.display === 'block' ? 'none' : 'block';
    });

    document.addEventListener('click', (e) => {
        if (!e.target.closest('.mode-toggle') && !e.target.closest('.mode-help-tooltip')) {
            modeHelpTooltip.style.display = 'none';
        }
    });

    // Upload
    initializeUpload();

    // Documents
    initDocumentsEvents();

    // Profile
    initProfileEvents();
}
