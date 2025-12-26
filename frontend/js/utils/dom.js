/**
 * DOM Utilities
 *
 * Fonctions utilitaires pour la manipulation du DOM
 */

/**
 * Echappe les caracteres HTML speciaux
 * @param {string} text - Texte a echapper
 * @returns {string} Texte echappe
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * Scroll vers le bas du container de messages
 */
function scrollToBottom() {
    const container = document.getElementById('messagesContainer');
    if (container) {
        container.scrollTop = container.scrollHeight;
    }
}

/**
 * Recupere un element par ID avec verification
 * @param {string} id - ID de l'element
 * @returns {HTMLElement|null}
 */
function getElement(id) {
    return document.getElementById(id);
}

/**
 * Ajoute un event listener avec delegation
 * @param {HTMLElement} parent - Element parent
 * @param {string} selector - Selecteur CSS des enfants
 * @param {string} event - Type d'evenement
 * @param {Function} handler - Callback
 */
function delegateEvent(parent, selector, event, handler) {
    parent.addEventListener(event, (e) => {
        const target = e.target.closest(selector);
        if (target && parent.contains(target)) {
            handler(e, target);
        }
    });
}

// Export global
window.DomUtils = {
    escapeHtml,
    scrollToBottom,
    getElement,
    delegateEvent
};

// Exports individuels pour compatibilite
window.escapeHtml = escapeHtml;
window.scrollToBottom = scrollToBottom;
