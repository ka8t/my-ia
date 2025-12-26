/**
 * Settings Module
 *
 * Gestion des preferences utilisateur (theme, sources, mode par defaut)
 * Note: API_URL et TOP_K sont geres par l'admin via .env
 */

/**
 * Initialise le theme
 */
function initializeTheme() {
    document.documentElement.setAttribute('data-theme', window.CONFIG.theme);
}

/**
 * Bascule entre les themes clair et sombre
 */
function toggleTheme() {
    window.CONFIG.theme = window.CONFIG.theme === 'light' ? 'dark' : 'light';
    localStorage.setItem('theme', window.CONFIG.theme);
    document.documentElement.setAttribute('data-theme', window.CONFIG.theme);

    // Sauvegarder dans le backend
    ApiService.updatePreferences({ theme: window.CONFIG.theme }).catch(console.error);
}

/**
 * Charge les preferences depuis le backend
 */
async function loadPreferences() {
    try {
        const prefs = await ApiService.getPreferences();
        window.CONFIG.showSources = prefs.show_sources;
        window.CONFIG.theme = prefs.theme;
        window.CONFIG.defaultModeId = prefs.default_mode_id;

        // Appliquer le theme
        document.documentElement.setAttribute('data-theme', window.CONFIG.theme);
        localStorage.setItem('theme', window.CONFIG.theme);

        // Mettre a jour les champs du panneau preferences
        const showSourcesEl = document.getElementById('showSources');
        const defaultModeEl = document.getElementById('defaultMode');

        if (showSourcesEl) showSourcesEl.checked = window.CONFIG.showSources;
        if (defaultModeEl) defaultModeEl.value = window.CONFIG.defaultModeId;

    } catch (error) {
        console.error('Error loading preferences:', error);
    }
}

/**
 * Charge les preferences dans le formulaire
 */
function loadSettings() {
    const showSourcesEl = document.getElementById('showSources');
    const defaultModeEl = document.getElementById('defaultMode');

    if (showSourcesEl) showSourcesEl.checked = window.CONFIG.showSources;
    if (defaultModeEl) defaultModeEl.value = window.CONFIG.defaultModeId;
}

/**
 * Sauvegarde les preferences utilisateur
 */
async function saveSettings() {
    const showSourcesEl = document.getElementById('showSources');
    const defaultModeEl = document.getElementById('defaultMode');

    window.CONFIG.showSources = showSourcesEl ? showSourcesEl.checked : false;
    window.CONFIG.defaultModeId = defaultModeEl ? parseInt(defaultModeEl.value) : 1;

    // Sauvegarder dans le backend
    try {
        await ApiService.updatePreferences({
            show_sources: window.CONFIG.showSources,
            default_mode_id: window.CONFIG.defaultModeId
        });
        showToast('Preferences enregistrees !', 'success');
    } catch (error) {
        console.error('Error saving preferences:', error);
        showToast('Erreur lors de la sauvegarde', 'error');
    }

    document.getElementById('closeSettings').click();
}

/**
 * Affiche les informations utilisateur
 */
function displayUserInfo() {
    const user = AuthService.getUser();
    if (user) {
        document.getElementById('userEmail').textContent = user.email;
    }
}

// Export global
window.SettingsModule = {
    initializeTheme,
    toggleTheme,
    loadPreferences,
    loadSettings,
    saveSettings,
    displayUserInfo
};

// Exports individuels
window.initializeTheme = initializeTheme;
window.toggleTheme = toggleTheme;
window.loadPreferences = loadPreferences;
window.loadSettings = loadSettings;
window.saveSettings = saveSettings;
window.displayUserInfo = displayUserInfo;
