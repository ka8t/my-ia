/**
 * Toast Component
 *
 * Affiche des notifications toast stylees
 *
 * Usage:
 *   showToast('Message', 'success');
 *   showToast('Erreur', 'error', 'Titre personnalise');
 */

const TOAST_ICONS = {
    success: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>
        <polyline points="22 4 12 14.01 9 11.01"/>
    </svg>`,
    error: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <circle cx="12" cy="12" r="10"/>
        <line x1="15" y1="9" x2="9" y2="15"/>
        <line x1="9" y1="9" x2="15" y2="15"/>
    </svg>`,
    info: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <circle cx="12" cy="12" r="10"/>
        <line x1="12" y1="16" x2="12" y2="12"/>
        <line x1="12" y1="8" x2="12.01" y2="8"/>
    </svg>`,
    warning: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
        <line x1="12" y1="9" x2="12" y2="13"/>
        <line x1="12" y1="17" x2="12.01" y2="17"/>
    </svg>`
};

const TOAST_TITLES = {
    success: 'Succes',
    error: 'Erreur',
    info: 'Information',
    warning: 'Attention'
};

/**
 * Recupere ou cree le container de toasts
 * @returns {HTMLElement}
 */
function getToastContainer() {
    let container = document.getElementById('toastContainer');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toastContainer';
        container.className = 'toast-container';
        document.body.appendChild(container);
    }
    return container;
}

/**
 * Affiche une notification toast
 * @param {string} message - Message a afficher
 * @param {string} type - Type: 'success', 'error', 'info', 'warning'
 * @param {string|null} title - Titre personnalise (optionnel)
 * @param {number} duration - Duree en ms (0 = permanent)
 * @returns {HTMLElement} Element toast cree
 */
function showToast(message, type = 'info', title = null, duration = 4000) {
    const container = getToastContainer();

    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.innerHTML = `
        <div class="toast-icon">${TOAST_ICONS[type] || TOAST_ICONS.info}</div>
        <div class="toast-content">
            <div class="toast-title">${title || TOAST_TITLES[type]}</div>
            <div class="toast-message">${escapeHtml(message)}</div>
        </div>
        <button class="toast-close">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <line x1="18" y1="6" x2="6" y2="18"/>
                <line x1="6" y1="6" x2="18" y2="18"/>
            </svg>
        </button>
    `;

    container.appendChild(toast);

    const closeBtn = toast.querySelector('.toast-close');
    const closeToast = () => {
        toast.classList.add('toast-exit');
        setTimeout(() => toast.remove(), 300);
    };

    closeBtn.addEventListener('click', closeToast);

    if (duration > 0) {
        setTimeout(closeToast, duration);
    }

    return toast;
}

// Export global
window.showToast = showToast;
window.ToastComponent = { showToast, getToastContainer };
