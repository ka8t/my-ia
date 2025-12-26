/**
 * Format Utilities
 *
 * Fonctions de formatage (dates, tailles, etc.)
 */

/**
 * Formate une heure a partir d'un timestamp
 * @param {string} timestamp - Timestamp ISO
 * @returns {string} Heure formatee (HH:MM)
 */
function formatTime(timestamp) {
    const date = new Date(timestamp);
    return date.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' });
}

/**
 * Formate une date relative (Aujourd'hui, Hier, etc.)
 * @param {string} timestamp - Timestamp ISO
 * @returns {string} Date formatee
 */
function formatDate(timestamp) {
    const date = new Date(timestamp);
    const now = new Date();
    const diffDays = Math.floor((now - date) / (1000 * 60 * 60 * 24));

    if (diffDays === 0) return 'Aujourd\'hui';
    if (diffDays === 1) return 'Hier';
    if (diffDays < 7) return `Il y a ${diffDays} jours`;

    return date.toLocaleDateString('fr-FR', { day: 'numeric', month: 'short' });
}

/**
 * Formate une taille de fichier en bytes/KB/MB
 * @param {number} bytes - Taille en bytes
 * @returns {string} Taille formatee
 */
function formatFileSize(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

/**
 * Formate un nombre de secondes en string
 * @param {number} seconds - Nombre de secondes
 * @returns {string} Temps formate
 */
function formatDuration(seconds) {
    if (seconds < 60) return `${seconds.toFixed(1)}s`;
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}m ${secs.toFixed(0)}s`;
}

// Export global
window.FormatUtils = {
    formatTime,
    formatDate,
    formatFileSize,
    formatDuration
};

// Exports individuels pour compatibilite
window.formatTime = formatTime;
window.formatDate = formatDate;
window.formatFileSize = formatFileSize;
