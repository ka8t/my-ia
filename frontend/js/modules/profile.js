/**
 * Profile Module
 *
 * Gestion du profil utilisateur:
 * - Affichage et modification des informations personnelles
 * - Changement de mot de passe
 * - Selection pays/ville avec autocompletion
 */

const ProfileModule = {
    // Cache des donnees
    profile: null,
    countries: [],
    selectedCityId: null,
    citySearchTimeout: null,

    /**
     * Ouvre la modal profil
     */
    async open() {
        const modal = document.getElementById('profileModal');
        if (!modal) return;

        modal.style.display = 'flex';
        this.showTab('info'); // Onglet par defaut

        // Charger le profil
        await this.loadProfile();
    },

    /**
     * Ferme la modal profil
     */
    close() {
        const modal = document.getElementById('profileModal');
        if (modal) {
            modal.style.display = 'none';
        }
        // Reset formulaires
        this.resetForms();
    },

    /**
     * Affiche un onglet specifique
     * @param {string} tabName - 'info' ou 'password'
     */
    showTab(tabName) {
        // Mettre a jour les boutons d'onglet
        document.querySelectorAll('.profile-tab-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.tab === tabName);
        });

        // Afficher le contenu correspondant
        document.querySelectorAll('.profile-tab-content').forEach(content => {
            content.classList.toggle('active', content.id === `profileTab${tabName.charAt(0).toUpperCase() + tabName.slice(1)}`);
        });
    },

    /**
     * Charge le profil depuis l'API
     */
    async loadProfile() {
        try {
            this.showLoading(true);
            this.profile = await ApiService.getProfile();
            this.populateForm();
            this.showLoading(false);
        } catch (error) {
            console.error('Error loading profile:', error);
            showToast('Erreur lors du chargement du profil', 'error');
            this.showLoading(false);
        }
    },

    /**
     * Charge la liste des pays
     */
    async loadCountries() {
        if (this.countries.length > 0) return;

        try {
            this.countries = await ApiService.getCountries();
            this.populateCountrySelect();
        } catch (error) {
            console.error('Error loading countries:', error);
        }
    },

    /**
     * Remplit le select des pays
     */
    populateCountrySelect() {
        const select = document.getElementById('profileCountry');
        if (!select) return;

        select.innerHTML = '<option value="">-- Selectionner un pays --</option>';
        this.countries.forEach(country => {
            const option = document.createElement('option');
            option.value = country.code;
            option.textContent = `${country.flag || ''} ${country.name}`;
            select.appendChild(option);
        });

        // Selectionner le pays actuel si present, sinon France par defaut
        if (this.profile && this.profile.country_code) {
            select.value = this.profile.country_code;
        } else {
            select.value = 'FR'; // France par defaut
        }
    },

    /**
     * Remplit le formulaire avec les donnees du profil
     */
    populateForm() {
        if (!this.profile) return;

        // Charger les pays
        this.loadCountries();

        // Header - Avatar et infos
        const displayName = this.profile.first_name || this.profile.username || this.profile.email.split('@')[0];
        const avatarEl = document.getElementById('profileAvatar');
        const usernameDisplayEl = document.getElementById('profileUsernameDisplay');
        const emailDisplayEl = document.getElementById('profileEmailDisplay');

        if (avatarEl) {
            avatarEl.textContent = displayName.charAt(0).toUpperCase();
        }
        if (usernameDisplayEl) {
            usernameDisplayEl.textContent = this.profile.username || displayName;
        }
        if (emailDisplayEl) {
            emailDisplayEl.textContent = this.profile.email;
        }

        // Informations de base
        const emailEl = document.getElementById('profileEmail');
        const usernameEl = document.getElementById('profileUsername');
        const firstNameEl = document.getElementById('profileFirstName');
        const lastNameEl = document.getElementById('profileLastName');
        const phoneEl = document.getElementById('profilePhone');
        const addressLine1El = document.getElementById('profileAddressLine1');
        const addressLine2El = document.getElementById('profileAddressLine2');
        const countryEl = document.getElementById('profileCountry');
        const cityInputEl = document.getElementById('profileCityInput');

        // Remplir les champs non modifiables (email et username)
        if (emailEl) emailEl.value = this.profile.email || '';
        if (usernameEl) usernameEl.value = this.profile.username || '';

        // Remplir les champs avec placeholders dynamiques
        this.setFieldValue(firstNameEl, this.profile.first_name);
        this.setFieldValue(lastNameEl, this.profile.last_name);
        this.setFieldValue(phoneEl, this.profile.phone);
        this.setFieldValue(addressLine1El, this.profile.address_line1);
        this.setFieldValue(addressLine2El, this.profile.address_line2);

        // Pays
        if (countryEl && this.profile.country_code) {
            countryEl.value = this.profile.country_code;
        }

        // Ville - afficher le nom si present
        if (cityInputEl) {
            if (this.profile.city_name) {
                cityInputEl.value = this.profile.city_name;
                if (this.profile.city_postal_code) {
                    cityInputEl.value += ` (${this.profile.city_postal_code})`;
                }
            } else {
                cityInputEl.value = '';
            }
            this.selectedCityId = this.profile.city_id || null;
        }

        // Statut verification
        const verifiedBadge = document.getElementById('profileVerifiedBadge');
        if (verifiedBadge) {
            verifiedBadge.style.display = this.profile.is_verified ? 'inline-flex' : 'none';
        }

        // Dates
        const createdEl = document.getElementById('profileCreatedAt');
        if (createdEl && this.profile.created_at) {
            const date = new Date(this.profile.created_at);
            createdEl.textContent = `Membre depuis ${date.toLocaleDateString('fr-FR', { month: 'long', year: 'numeric' })}`;
        }

        // Initialiser les placeholders dynamiques
        this.initDynamicPlaceholders();
    },

    /**
     * Definit la valeur d'un champ ou le placeholder dynamique
     * @param {HTMLElement} field
     * @param {string} value
     */
    setFieldValue(field, value) {
        if (!field) return;

        if (value) {
            field.value = value;
            field.classList.remove('placeholder-active');
        } else {
            const label = field.dataset.label || '';
            field.value = label ? `Veuillez saisir ${label}` : '';
            if (label) field.classList.add('placeholder-active');
        }
    },

    /**
     * Initialise les placeholders dynamiques sur tous les champs
     */
    initDynamicPlaceholders() {
        const fields = document.querySelectorAll('#profileTabInfo input[data-label]');

        fields.forEach(field => {
            const label = field.dataset.label;
            const placeholderText = `Veuillez saisir ${label}`;

            // Focus - effacer le placeholder
            field.addEventListener('focus', () => {
                if (field.classList.contains('placeholder-active')) {
                    field.value = '';
                    field.classList.remove('placeholder-active');
                }
            });

            // Blur - remettre le placeholder si vide
            field.addEventListener('blur', () => {
                if (!field.value.trim()) {
                    field.value = placeholderText;
                    field.classList.add('placeholder-active');
                }
            });
        });
    },

    /**
     * Recherche des villes avec debounce
     * @param {string} query
     */
    async searchCities(query) {
        const resultsContainer = document.getElementById('profileCityResults');
        if (!resultsContainer) return;

        // Minimum 2 caracteres
        if (query.length < 2) {
            resultsContainer.style.display = 'none';
            return;
        }

        // Debounce
        clearTimeout(this.citySearchTimeout);
        this.citySearchTimeout = setTimeout(async () => {
            try {
                const countryCode = document.getElementById('profileCountry')?.value || 'FR';
                const cities = await ApiService.searchCities(query, countryCode, 10);

                if (cities.length === 0) {
                    resultsContainer.innerHTML = '<div class="city-result-empty">Aucune ville trouvee</div>';
                } else {
                    resultsContainer.innerHTML = cities.map(city => `
                        <div class="city-result-item" data-id="${city.id}" data-name="${city.name}" data-postal="${city.postal_code || ''}" data-display="${city.display || city.name}">
                            <span class="city-name">${city.display || city.name}</span>
                        </div>
                    `).join('');

                    // Event listeners pour selection (mousedown se declenche avant blur)
                    resultsContainer.querySelectorAll('.city-result-item').forEach(item => {
                        item.addEventListener('mousedown', (e) => {
                            e.preventDefault(); // Empeche le blur
                            this.selectCity(
                                parseInt(item.dataset.id),
                                item.dataset.name,
                                item.dataset.postal
                            );
                        });
                    });
                }

                resultsContainer.style.display = 'block';
            } catch (error) {
                console.error('Error searching cities:', error);
                resultsContainer.style.display = 'none';
            }
        }, 300);
    },

    /**
     * Selectionne une ville
     * @param {number} id
     * @param {string} name
     * @param {string} postalCode
     */
    selectCity(id, name, postalCode) {
        const cityInput = document.getElementById('profileCityInput');
        const resultsContainer = document.getElementById('profileCityResults');

        if (cityInput) {
            cityInput.value = postalCode ? `${name} (${postalCode})` : name;
        }
        this.selectedCityId = id;

        if (resultsContainer) {
            resultsContainer.style.display = 'none';
        }
    },

    /**
     * Recupere la valeur reelle d'un champ (ignore les placeholders)
     * @param {string} fieldId
     * @returns {string|null}
     */
    getFieldRealValue(fieldId) {
        const field = document.getElementById(fieldId);
        if (!field) return null;

        // Si le champ a la classe placeholder-active, il contient le placeholder
        if (field.classList.contains('placeholder-active')) {
            return '';
        }

        return field.value?.trim() || '';
    },

    /**
     * Valide les champs obligatoires (min 4 caracteres)
     * @returns {Object} {valid: boolean, errors: string[], invalidFields: string[]}
     */
    validateRequiredFields() {
        const errors = [];
        const invalidFields = [];
        const MIN_LENGTH = 4;

        // Fonction helper pour valider un champ
        const validateField = (fieldId, label, minLen = MIN_LENGTH) => {
            const value = this.getFieldRealValue(fieldId);
            const field = document.getElementById(fieldId);

            if (!value || value.length < minLen) {
                errors.push(label);
                invalidFields.push(fieldId);
                if (field) field.classList.add('field-invalid');
            } else {
                if (field) field.classList.remove('field-invalid');
            }
        };

        // Champs obligatoires avec min 4 caracteres
        validateField('profileFirstName', 'Prénom');
        validateField('profileLastName', 'Nom');
        validateField('profilePhone', 'Téléphone');

        // Pays (select - juste verifier qu'il est selectionne)
        const countrySelect = document.getElementById('profileCountry');
        const countryCode = countrySelect?.value;
        if (!countryCode) {
            errors.push('Pays');
            invalidFields.push('profileCountry');
            if (countrySelect) countrySelect.classList.add('field-invalid');
        } else {
            if (countrySelect) countrySelect.classList.remove('field-invalid');
        }

        // Ville (verifier texte + selection)
        const cityInput = document.getElementById('profileCityInput');
        const cityValue = cityInput?.value?.trim();
        if (!cityValue || cityValue.length < MIN_LENGTH || !this.selectedCityId) {
            errors.push('Ville');
            invalidFields.push('profileCityInput');
            if (cityInput) cityInput.classList.add('field-invalid');
        } else {
            if (cityInput) cityInput.classList.remove('field-invalid');
        }

        return {
            valid: errors.length === 0,
            errors: errors,
            invalidFields: invalidFields
        };
    },

    /**
     * Retire le style d'erreur quand l'utilisateur modifie un champ
     */
    clearFieldError(fieldId) {
        const field = document.getElementById(fieldId);
        if (field) {
            field.classList.remove('field-invalid');
        }
    },

    /**
     * Sauvegarde le profil
     */
    async saveProfile() {
        const saveBtn = document.getElementById('profileSaveBtn');

        // Valider les champs obligatoires
        const validation = this.validateRequiredFields();
        if (!validation.valid) {
            const message = `Veuillez remplir les champs obligatoires : ${validation.errors.join(', ')}`;
            showToast(message, 'error');
            return;
        }

        try {
            if (saveBtn) {
                saveBtn.disabled = true;
                saveBtn.textContent = 'Enregistrement...';
            }

            const data = {};

            // Collecter les champs modifiables (ignore les placeholders)
            const firstName = this.getFieldRealValue('profileFirstName');
            const lastName = this.getFieldRealValue('profileLastName');
            const phone = this.getFieldRealValue('profilePhone');
            const addressLine1 = this.getFieldRealValue('profileAddressLine1');
            const addressLine2 = this.getFieldRealValue('profileAddressLine2');
            const countryCode = document.getElementById('profileCountry')?.value;

            // Inclure les champs avec valeur
            if (firstName) data.first_name = firstName;
            if (lastName) data.last_name = lastName;
            if (phone) data.phone = phone;
            if (addressLine1) data.address_line1 = addressLine1;
            if (addressLine2) data.address_line2 = addressLine2;
            if (countryCode) data.country_code = countryCode;
            if (this.selectedCityId) data.city_id = this.selectedCityId;

            // Permettre de vider les champs optionnels (sauf obligatoires)
            if (addressLine1 === '' && this.profile.address_line1) data.address_line1 = null;
            if (addressLine2 === '' && this.profile.address_line2) data.address_line2 = null;

            this.profile = await ApiService.updateProfile(data);
            showToast('Profil mis a jour avec succes', 'success');

            // Mettre a jour l'affichage utilisateur dans la sidebar
            displayUserInfo();

        } catch (error) {
            console.error('Error saving profile:', error);
            showToast(error.message || 'Erreur lors de la sauvegarde', 'error');
        } finally {
            if (saveBtn) {
                saveBtn.disabled = false;
                saveBtn.textContent = 'Enregistrer';
            }
        }
    },

    /**
     * Change le mot de passe
     */
    async changePassword() {
        const currentPassword = document.getElementById('profileCurrentPassword')?.value;
        const newPassword = document.getElementById('profileNewPassword')?.value;
        const confirmPassword = document.getElementById('profileConfirmPassword')?.value;
        const changeBtn = document.getElementById('profileChangePasswordBtn');
        const errorEl = document.getElementById('profilePasswordError');

        // Validation basique
        if (!currentPassword || !newPassword || !confirmPassword) {
            if (errorEl) {
                errorEl.textContent = 'Tous les champs sont obligatoires';
                errorEl.style.display = 'block';
            }
            return;
        }

        if (newPassword !== confirmPassword) {
            if (errorEl) {
                errorEl.textContent = 'Les mots de passe ne correspondent pas';
                errorEl.style.display = 'block';
            }
            return;
        }

        if (newPassword.length < 8) {
            if (errorEl) {
                errorEl.textContent = 'Le nouveau mot de passe doit contenir au moins 8 caracteres';
                errorEl.style.display = 'block';
            }
            return;
        }

        try {
            if (changeBtn) {
                changeBtn.disabled = true;
                changeBtn.textContent = 'Modification...';
            }
            if (errorEl) errorEl.style.display = 'none';

            await ApiService.changePassword(currentPassword, newPassword, confirmPassword);

            showToast('Mot de passe modifie avec succes', 'success');

            // Vider les champs
            document.getElementById('profileCurrentPassword').value = '';
            document.getElementById('profileNewPassword').value = '';
            document.getElementById('profileConfirmPassword').value = '';

        } catch (error) {
            console.error('Error changing password:', error);
            if (errorEl) {
                errorEl.textContent = error.message || 'Erreur lors du changement de mot de passe';
                errorEl.style.display = 'block';
            }
        } finally {
            if (changeBtn) {
                changeBtn.disabled = false;
                changeBtn.textContent = 'Modifier le mot de passe';
            }
        }
    },

    /**
     * Affiche/cache le loader
     * @param {boolean} show
     */
    showLoading(show) {
        const loader = document.getElementById('profileLoader');
        const content = document.getElementById('profileContent');

        if (loader) loader.style.display = show ? 'flex' : 'none';
        if (content) content.style.display = show ? 'none' : 'block';
    },

    /**
     * Reset les formulaires
     */
    resetForms() {
        // Reset password form
        const pwdForm = document.getElementById('profilePasswordForm');
        if (pwdForm) pwdForm.reset();

        const errorEl = document.getElementById('profilePasswordError');
        if (errorEl) errorEl.style.display = 'none';

        // Reset city results
        const cityResults = document.getElementById('profileCityResults');
        if (cityResults) cityResults.style.display = 'none';
    },

    /**
     * Initialise les event listeners
     */
    init() {
        // Bouton pour ouvrir la modal (clic sur user info)
        const userInfo = document.getElementById('userInfo');
        if (userInfo) {
            userInfo.addEventListener('click', () => this.open());
            userInfo.style.cursor = 'pointer';
        }

        // Bouton dans les preferences pour ouvrir le profil
        const openFromSettings = document.getElementById('openProfileFromSettings');
        if (openFromSettings) {
            openFromSettings.addEventListener('click', () => {
                // Fermer le panneau des preferences
                const settingsPanel = document.getElementById('settingsPanel');
                if (settingsPanel) {
                    settingsPanel.classList.remove('open');
                    setTimeout(() => {
                        settingsPanel.style.display = 'none';
                    }, 300);
                }
                // Ouvrir la modal profil
                this.open();
            });
        }

        // Fermer la modal
        const closeBtn = document.getElementById('closeProfileModal');
        if (closeBtn) {
            closeBtn.addEventListener('click', () => this.close());
        }

        // Boutons Annuler
        const cancelBtn = document.getElementById('profileCancelBtn');
        if (cancelBtn) {
            cancelBtn.addEventListener('click', () => this.close());
        }

        const passwordCancelBtn = document.getElementById('profilePasswordCancelBtn');
        if (passwordCancelBtn) {
            passwordCancelBtn.addEventListener('click', () => this.close());
        }

        // Fermer en cliquant en dehors
        const modal = document.getElementById('profileModal');
        if (modal) {
            modal.addEventListener('click', (e) => {
                if (e.target === modal) this.close();
            });
        }

        // Fermer avec la touche Escape
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                const profileModal = document.getElementById('profileModal');
                if (profileModal && profileModal.style.display !== 'none') {
                    this.close();
                }
            }
        });

        // Onglets
        document.querySelectorAll('.profile-tab-btn').forEach(btn => {
            btn.addEventListener('click', () => this.showTab(btn.dataset.tab));
        });

        // Sauvegarder le profil
        const saveBtn = document.getElementById('profileSaveBtn');
        if (saveBtn) {
            saveBtn.addEventListener('click', () => this.saveProfile());
        }

        // Changer le mot de passe
        const changePasswordBtn = document.getElementById('profileChangePasswordBtn');
        if (changePasswordBtn) {
            changePasswordBtn.addEventListener('click', () => this.changePassword());
        }

        // Recherche de ville
        const cityInput = document.getElementById('profileCityInput');
        if (cityInput) {
            cityInput.addEventListener('input', (e) => {
                this.searchCities(e.target.value);
                this.clearFieldError('profileCityInput');
            });

            // Fermer les resultats quand on quitte le champ
            cityInput.addEventListener('blur', () => {
                setTimeout(() => {
                    const resultsContainer = document.getElementById('profileCityResults');
                    if (resultsContainer) resultsContainer.style.display = 'none';
                }, 200);
            });
        }

        // Reset city selection quand on change de pays
        const countrySelect = document.getElementById('profileCountry');
        if (countrySelect) {
            countrySelect.addEventListener('change', () => {
                const cityInput = document.getElementById('profileCityInput');
                if (cityInput) cityInput.value = '';
                this.selectedCityId = null;
                this.clearFieldError('profileCountry');
            });
        }

        // Enlever le highlight d'erreur quand l'utilisateur tape dans les champs obligatoires
        const requiredFields = ['profileFirstName', 'profileLastName', 'profilePhone'];
        requiredFields.forEach(fieldId => {
            const field = document.getElementById(fieldId);
            if (field) {
                field.addEventListener('input', () => this.clearFieldError(fieldId));
            }
        });
    }
};

// Export global
window.ProfileModule = ProfileModule;

// Fonction helper pour l'initialisation
function initProfileEvents() {
    ProfileModule.init();
}

window.initProfileEvents = initProfileEvents;
