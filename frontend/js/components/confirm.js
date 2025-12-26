/**
 * Confirm Component
 *
 * Affiche une modale de confirmation stylisee
 *
 * Usage:
 *   const confirmed = await showConfirm({
 *     title: 'Supprimer ?',
 *     message: 'Cette action est irreversible.',
 *     type: 'danger'
 *   });
 *   if (confirmed) { ... }
 */

/**
 * Affiche une modale de confirmation
 * @param {Object} options - Options de la modale
 * @param {string} options.title - Titre de la modale
 * @param {string} options.message - Message de confirmation
 * @param {string} options.confirmText - Texte du bouton confirmer
 * @param {string} options.cancelText - Texte du bouton annuler
 * @param {string} options.type - Type: 'danger', 'warning', 'info'
 * @param {string|null} options.icon - SVG personnalise (optionnel)
 * @returns {Promise<boolean>} True si confirme, false sinon
 */
function showConfirm(options) {
    return new Promise((resolve) => {
        const {
            title = 'Confirmation',
            message = 'Etes-vous sur ?',
            confirmText = 'Confirmer',
            cancelText = 'Annuler',
            type = 'warning',
            icon = null
        } = options;

        const iconSvg = icon || (type === 'danger' ? `
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M3 6h18M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2"/>
            </svg>
        ` : `
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
                <line x1="12" y1="9" x2="12" y2="13"/>
                <line x1="12" y1="17" x2="12.01" y2="17"/>
            </svg>
        `);

        const modal = document.createElement('div');
        modal.className = 'confirm-modal';
        modal.innerHTML = `
            <div class="confirm-modal-content">
                <div class="confirm-modal-icon confirm-${type}">${iconSvg}</div>
                <div class="confirm-modal-title">${escapeHtml(title)}</div>
                <div class="confirm-modal-message">${escapeHtml(message)}</div>
                <div class="confirm-modal-actions">
                    <button class="btn-confirm-cancel">${escapeHtml(cancelText)}</button>
                    <button class="btn-confirm-ok ${type === 'danger' ? 'btn-danger' : ''}">${escapeHtml(confirmText)}</button>
                </div>
            </div>
        `;

        document.body.appendChild(modal);

        const closeModal = (result) => {
            modal.remove();
            resolve(result);
        };

        // Event listeners
        modal.querySelector('.btn-confirm-cancel').addEventListener('click', () => closeModal(false));
        modal.querySelector('.btn-confirm-ok').addEventListener('click', () => closeModal(true));

        // Fermer avec Escape
        const handleEscape = (e) => {
            if (e.key === 'Escape') {
                document.removeEventListener('keydown', handleEscape);
                closeModal(false);
            }
        };
        document.addEventListener('keydown', handleEscape);

        // Clic en dehors ferme aussi
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                closeModal(false);
            }
        });

        // Focus sur le bouton OK
        modal.querySelector('.btn-confirm-ok').focus();
    });
}

// Export global
window.showConfirm = showConfirm;
window.ConfirmComponent = { showConfirm };
