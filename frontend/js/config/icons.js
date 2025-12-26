/**
 * Configuration centralisee des icones SVG
 *
 * Ce fichier centralise toutes les icones utilisees dans l'application.
 * Pour modifier une icone ou son tooltip, modifiez uniquement ce fichier.
 *
 * Usage:
 *   - Icons.render('required')           // Retourne le SVG
 *   - Icons.render('required', 16)       // Retourne le SVG avec taille personnalisee
 *   - Icons.getTooltip('required')       // Retourne le tooltip
 *   - Icons.renderWithTooltip('required') // Retourne SVG + tooltip pour legendes
 *   - Icons.renderLegend(['required', 'encrypted']) // Genere la legende complete
 */

const Icons = {
    // ==========================================================================
    // DEFINITIONS DES ICONES
    // ==========================================================================

    definitions: {
        /**
         * Icone "Obligatoire" - Point d'exclamation dans un cercle
         */
        required: {
            name: 'required',
            label: 'Obligatoire',
            tooltip: 'Ce champ est obligatoire',
            cssClass: 'required-icon',
            color: 'var(--warning-color)',
            viewBox: '0 0 24 24',
            path: `<circle cx="12" cy="12" r="10"/>
                   <line x1="12" y1="8" x2="12" y2="12"/>
                   <line x1="12" y1="16" x2="12.01" y2="16"/>`
        },

        /**
         * Icone "Chiffré" - Cadenas ferme
         */
        encrypted: {
            name: 'encrypted',
            label: 'Chiffré',
            tooltip: 'Ce champ est chiffré en base de données',
            cssClass: 'encrypted-icon',
            color: 'var(--accent-color)',
            viewBox: '0 0 24 24',
            path: `<rect x="3" y="11" width="18" height="11" rx="2" ry="2"/>
                   <path d="M7 11V7a5 5 0 0 1 10 0v4"/>`
        },

        /**
         * Icone "Non modifiable" - Cercle barre
         */
        readonly: {
            name: 'readonly',
            label: 'Non modifiable',
            tooltip: 'Ce champ ne peut pas etre modifie',
            cssClass: 'readonly-icon',
            color: 'var(--text-secondary)',
            viewBox: '0 0 24 24',
            path: `<circle cx="12" cy="12" r="10"/>
                   <line x1="4.93" y1="4.93" x2="19.07" y2="19.07"/>`
        },

        /**
         * Icone "Verifie" - Coche dans un cercle
         */
        verified: {
            name: 'verified',
            label: 'Vérifié',
            tooltip: 'Ce compte a ete verifie',
            cssClass: 'verified-icon',
            color: 'var(--accent-color)',
            viewBox: '0 0 24 24',
            path: `<path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>
                   <polyline points="22 4 12 14.01 9 11.01"/>`
        },

        /**
         * Icone "Information" - i dans un cercle
         */
        info: {
            name: 'info',
            label: 'Information',
            tooltip: 'Information supplementaire',
            cssClass: 'info-icon',
            color: 'var(--info-color)',
            viewBox: '0 0 24 24',
            path: `<circle cx="12" cy="12" r="10"/>
                   <line x1="12" y1="16" x2="12" y2="12"/>
                   <line x1="12" y1="8" x2="12.01" y2="8"/>`
        },

        /**
         * Icone "Erreur" - X dans un cercle
         */
        error: {
            name: 'error',
            label: 'Erreur',
            tooltip: 'Une erreur est survenue',
            cssClass: 'error-icon',
            color: 'var(--danger-color)',
            viewBox: '0 0 24 24',
            path: `<circle cx="12" cy="12" r="10"/>
                   <line x1="15" y1="9" x2="9" y2="15"/>
                   <line x1="9" y1="9" x2="15" y2="15"/>`
        },

        /**
         * Icone "Succes" - Coche
         */
        success: {
            name: 'success',
            label: 'Succès',
            tooltip: 'Operation reussie',
            cssClass: 'success-icon',
            color: 'var(--success-color)',
            viewBox: '0 0 24 24',
            path: `<polyline points="20 6 9 17 4 12"/>`
        },

        /**
         * Icone "Avertissement" - Triangle avec exclamation
         */
        warning: {
            name: 'warning',
            label: 'Attention',
            tooltip: 'Attention requise',
            cssClass: 'warning-icon',
            color: 'var(--warning-color)',
            viewBox: '0 0 24 24',
            path: `<path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
                   <line x1="12" y1="9" x2="12" y2="13"/>
                   <line x1="12" y1="17" x2="12.01" y2="17"/>`
        }
    },

    // ==========================================================================
    // METHODES PUBLIQUES
    // ==========================================================================

    /**
     * Genere le SVG d'une icone
     * @param {string} name - Nom de l'icone
     * @param {number} size - Taille en pixels (defaut: 14)
     * @returns {string} - Code SVG
     */
    render(name, size = 14) {
        const icon = this.definitions[name];
        if (!icon) {
            console.warn(`Icons: icone "${name}" non trouvee`);
            return '';
        }

        return `<svg class="${icon.cssClass}" width="${size}" height="${size}" viewBox="${icon.viewBox}" fill="none" stroke="currentColor" stroke-width="2">
            ${icon.path}
        </svg>`;
    },

    /**
     * Retourne le tooltip d'une icone
     * @param {string} name - Nom de l'icone
     * @returns {string} - Texte du tooltip
     */
    getTooltip(name) {
        const icon = this.definitions[name];
        return icon ? icon.tooltip : '';
    },

    /**
     * Retourne le label court d'une icone
     * @param {string} name - Nom de l'icone
     * @returns {string} - Label
     */
    getLabel(name) {
        const icon = this.definitions[name];
        return icon ? icon.label : '';
    },

    /**
     * Genere un element de legende (icone + label)
     * @param {string} name - Nom de l'icone
     * @param {number} size - Taille de l'icone (defaut: 12)
     * @returns {string} - HTML de l'element de legende
     */
    renderLegendItem(name, size = 12) {
        const icon = this.definitions[name];
        if (!icon) return '';

        return `<span class="legend-item">
            ${this.render(name, size)}
            ${icon.label}
        </span>`;
    },

    /**
     * Genere une legende complete avec plusieurs icones
     * @param {string[]} iconNames - Liste des noms d'icones
     * @param {string} title - Titre de la legende (defaut: "Legende :")
     * @returns {string} - HTML de la legende
     */
    renderLegend(iconNames, title = 'Légende :') {
        const items = iconNames
            .map(name => this.renderLegendItem(name))
            .filter(item => item !== '')
            .join('\n');

        return `<div class="profile-legend">
            <span class="legend-title">${title}</span>
            ${items}
        </div>`;
    },

    /**
     * Genere un label de champ avec icones
     * @param {string} fieldId - ID du champ
     * @param {string} labelText - Texte du label
     * @param {string[]} iconNames - Liste des icones a afficher
     * @returns {string} - HTML du label complet
     */
    renderFieldLabel(fieldId, labelText, iconNames = []) {
        const icons = iconNames.map(name => this.render(name)).join('');
        return `<label for="${fieldId}">
            ${icons}
            ${labelText}
        </label>`;
    },

    /**
     * Liste toutes les icones disponibles
     * @returns {string[]} - Noms des icones
     */
    list() {
        return Object.keys(this.definitions);
    },

    /**
     * Retourne la definition complete d'une icone
     * @param {string} name - Nom de l'icone
     * @returns {Object|null} - Definition de l'icone
     */
    get(name) {
        return this.definitions[name] || null;
    }
};

// Export global
window.Icons = Icons;
