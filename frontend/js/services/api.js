/**
 * Service API
 * Gere tous les appels au backend avec authentification JWT
 * Note: Mode debug centralise dans config.js (window.DEBUG)
 */

const ApiService = {
    /**
     * Effectue une requete API authentifiee
     * @param {string} endpoint
     * @param {object} options
     * @returns {Promise<Response>}
     */
    async request(endpoint, options = {}) {
        const url = `${AuthService.getApiUrl()}${endpoint}`;

        const headers = {
            ...AuthService.getAuthHeaders(),
            ...options.headers
        };

        // Ajouter Content-Type si body present et pas FormData
        if (options.body && !(options.body instanceof FormData)) {
            headers['Content-Type'] = 'application/json';
        }

        // Debug: log request
        if (window.DEBUG) {
            console.log(`[API] ${options.method || 'GET'} ${endpoint}`, {
                headers: headers,
                body: options.body ? JSON.parse(options.body) : undefined
            });
        }

        const response = await fetch(url, {
            ...options,
            headers
        });

        // Debug: log response status
        if (window.DEBUG) {
            console.log(`[API] Response ${response.status} ${response.statusText} for ${endpoint}`);
        }

        // Si 401, rediriger vers login
        if (response.status === 401) {
            AuthService.logout();
            throw new Error('Session expiree');
        }

        return response;
    },

    // =========================================================================
    // CONVERSATIONS
    // =========================================================================

    /**
     * Liste les conversations de l'utilisateur
     * @param {number} limit
     * @param {number} offset
     * @returns {Promise<{items: Array, total: number}>}
     */
    async listConversations(limit = 50, offset = 0) {
        const response = await this.request(`/conversations/?limit=${limit}&offset=${offset}`);
        if (!response.ok) throw new Error('Erreur lors du chargement des conversations');
        return response.json();
    },

    /**
     * Cree une nouvelle conversation
     * @param {string} title
     * @param {number} modeId - 1=chatbot, 2=assistant
     * @returns {Promise<object>}
     */
    async createConversation(title, modeId = 1) {
        const response = await this.request('/conversations', {
            method: 'POST',
            body: JSON.stringify({ title, mode_id: modeId })
        });
        if (!response.ok) throw new Error('Erreur lors de la creation de la conversation');
        return response.json();
    },

    /**
     * Recupere une conversation avec ses messages
     * @param {string} conversationId
     * @returns {Promise<object>}
     */
    async getConversation(conversationId) {
        const response = await this.request(`/conversations/${conversationId}`);
        if (!response.ok) throw new Error('Conversation non trouvee');
        return response.json();
    },

    /**
     * Met a jour une conversation
     * @param {string} conversationId
     * @param {object} data
     * @returns {Promise<object>}
     */
    async updateConversation(conversationId, data) {
        const response = await this.request(`/conversations/${conversationId}`, {
            method: 'PATCH',
            body: JSON.stringify(data)
        });
        if (!response.ok) throw new Error('Erreur lors de la mise a jour');
        return response.json();
    },

    /**
     * Supprime une conversation
     * @param {string} conversationId
     * @returns {Promise<void>}
     */
    async deleteConversation(conversationId) {
        const response = await this.request(`/conversations/${conversationId}`, {
            method: 'DELETE'
        });
        if (!response.ok) throw new Error('Erreur lors de la suppression');
    },

    /**
     * Envoie un message et recupere la reponse (chat avec sauvegarde)
     * @param {string} conversationId
     * @param {string} query
     * @returns {Promise<object>}
     */
    async chatInConversation(conversationId, query) {
        const response = await this.request(`/conversations/${conversationId}/chat`, {
            method: 'POST',
            body: JSON.stringify({ query })
        });
        if (!response.ok) throw new Error('Erreur lors de l\'envoi du message');
        return response.json();
    },

    /**
     * Supprime des messages (soft delete)
     * @param {string} conversationId
     * @param {string[]} messageIds - Liste des IDs de messages a supprimer
     * @returns {Promise<{deleted_count: number}>}
     */
    async deleteMessages(conversationId, messageIds) {
        const response = await this.request(`/conversations/${conversationId}/messages`, {
            method: 'DELETE',
            body: JSON.stringify({ message_ids: messageIds })
        });
        if (!response.ok) throw new Error('Erreur lors de la suppression des messages');
        return response.json();
    },

    /**
     * Archive une conversation
     * @param {string} conversationId
     * @returns {Promise<object>}
     */
    async archiveConversation(conversationId) {
        const response = await this.request(`/conversations/${conversationId}/archive`, {
            method: 'POST'
        });
        if (!response.ok) throw new Error('Erreur lors de l\'archivage');
        return response.json();
    },

    /**
     * Desarchive une conversation
     * @param {string} conversationId
     * @returns {Promise<object>}
     */
    async unarchiveConversation(conversationId) {
        const response = await this.request(`/conversations/${conversationId}/unarchive`, {
            method: 'POST'
        });
        if (!response.ok) throw new Error('Erreur lors du desarchivage');
        return response.json();
    },

    /**
     * Ajoute un message a une conversation (sauvegarde en base)
     * Version silencieuse : ne deconnecte pas en cas d'erreur 401
     * @param {string} conversationId
     * @param {string} senderType - 'user' ou 'assistant'
     * @param {string} content
     * @param {object} sources - Sources RAG (optionnel)
     * @param {number} responseTime - Temps de reponse en secondes (optionnel)
     * @returns {Promise<object|null>}
     */
    async addMessage(conversationId, senderType, content, sources = null, responseTime = null) {
        const body = { sender_type: senderType, content };
        if (sources) {
            body.sources = sources;
        }
        if (responseTime !== null) {
            body.response_time = responseTime;
        }

        const url = `${AuthService.getApiUrl()}/conversations/${conversationId}/messages`;
        const headers = {
            ...AuthService.getAuthHeaders(),
            'Content-Type': 'application/json'
        };

        if (window.DEBUG) {
            console.log(`[API] POST /conversations/${conversationId}/messages (silent mode)`);
        }

        try {
            const response = await fetch(url, {
                method: 'POST',
                headers,
                body: JSON.stringify(body)
            });

            if (window.DEBUG) {
                console.log(`[API] Response ${response.status} for addMessage`);
            }

            // Ne pas deconnecter en cas de 401, juste retourner null
            if (!response.ok) {
                if (response.status === 401) {
                    console.warn('[API] Token expired during message save - message not persisted');
                }
                return null;
            }

            return response.json();
        } catch (error) {
            console.error('[API] Error saving message:', error);
            return null;
        }
    },

    // =========================================================================
    // CHAT STREAMING
    // =========================================================================

    /**
     * Envoie un message avec streaming
     * @param {string} query
     * @param {string} sessionId
     * @param {AbortSignal} signal
     * @returns {Promise<Response>}
     */
    async streamChat(query, sessionId, signal) {
        return this.request('/chat/stream', {
            method: 'POST',
            body: JSON.stringify({ query, session_id: sessionId }),
            signal
        });
    },

    // =========================================================================
    // DOCUMENTS - User Documents Management
    // =========================================================================

    /**
     * Liste les documents de l'utilisateur avec pagination
     * @param {object} options - {page, page_size, visibility, file_type}
     * @returns {Promise<{documents: Array, total: number, page: number, page_size: number, total_pages: number}>}
     */
    async listUserDocuments(options = {}) {
        const params = new URLSearchParams();
        if (options.page) params.append('page', options.page);
        if (options.page_size) params.append('page_size', options.page_size);
        if (options.visibility) params.append('visibility', options.visibility);
        if (options.file_type) params.append('file_type', options.file_type);

        const query = params.toString() ? `?${params.toString()}` : '';
        const response = await this.request(`/api/user/documents${query}`);
        if (!response.ok) throw new Error('Erreur lors du chargement des documents');
        return response.json();
    },

    /**
     * Recherche dans les documents de l'utilisateur
     * @param {string} query - Terme de recherche (min 2 chars)
     * @param {string} visibility - Filtre optionnel
     * @returns {Promise<{results: Array, total: number, query: string}>}
     */
    async searchUserDocuments(query, visibility = null) {
        const params = new URLSearchParams({ q: query });
        if (visibility) params.append('visibility', visibility);

        const response = await this.request(`/api/user/documents/search?${params.toString()}`);
        if (!response.ok) throw new Error('Erreur lors de la recherche');
        return response.json();
    },

    /**
     * Recupere les statistiques de stockage de l'utilisateur
     * @returns {Promise<{used_bytes: number, file_count: number, quota_bytes: number, quota_used_percent: number, remaining_bytes: number}>}
     */
    async getUserStorageStats() {
        const response = await this.request('/api/user/documents/stats');
        if (!response.ok) throw new Error('Erreur lors du chargement des statistiques');
        return response.json();
    },

    /**
     * Recupere les details d'un document avec ses versions
     * @param {string} documentId
     * @returns {Promise<object>}
     */
    async getUserDocument(documentId) {
        const response = await this.request(`/api/user/documents/${documentId}`);
        if (!response.ok) throw new Error('Document non trouve');
        return response.json();
    },

    /**
     * Upload un nouveau document
     * @param {File} file
     * @param {string} visibility - 'public' ou 'private'
     * @returns {Promise<object>}
     */
    async uploadUserDocument(file, visibility = 'public') {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('visibility', visibility);

        const response = await this.request('/api/user/documents', {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Erreur lors de l\'upload');
        }
        return response.json();
    },

    /**
     * Remplace un document par une nouvelle version
     * @param {string} documentId
     * @param {File} file
     * @param {string} comment - Note optionnelle
     * @returns {Promise<object>}
     */
    async replaceUserDocument(documentId, file, comment = null) {
        const formData = new FormData();
        formData.append('file', file);
        if (comment) formData.append('comment', comment);

        const response = await this.request(`/api/user/documents/${documentId}`, {
            method: 'PUT',
            body: formData
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Erreur lors du remplacement');
        }
        return response.json();
    },

    /**
     * Met a jour les metadonnees d'un document
     * @param {string} documentId
     * @param {object} data - {visibility, filename}
     * @returns {Promise<object>}
     */
    async updateUserDocument(documentId, data) {
        const response = await this.request(`/api/user/documents/${documentId}`, {
            method: 'PATCH',
            body: JSON.stringify(data)
        });
        if (!response.ok) throw new Error('Erreur lors de la mise a jour');
        return response.json();
    },

    /**
     * Supprime un document et toutes ses versions
     * @param {string} documentId
     * @returns {Promise<void>}
     */
    async deleteUserDocument(documentId) {
        const response = await this.request(`/api/user/documents/${documentId}`, {
            method: 'DELETE'
        });
        if (!response.ok) throw new Error('Erreur lors de la suppression');
    },

    /**
     * Telecharge un document
     * @param {string} documentId
     * @param {number} version - Version specifique (optionnel)
     * @returns {Promise<Blob>}
     */
    async downloadUserDocument(documentId, version = null) {
        const params = version ? `?version=${version}` : '';
        const response = await this.request(`/api/user/documents/${documentId}/download${params}`);
        if (!response.ok) throw new Error('Erreur lors du telechargement');
        return response.blob();
    },

    // =========================================================================
    // DOCUMENTS - Legacy Upload (pour compatibilite)
    // =========================================================================

    /**
     * Upload un fichier (legacy - utilise /upload/v2)
     * @param {File} file
     * @returns {Promise<object>}
     */
    async uploadFile(file) {
        const formData = new FormData();
        formData.append('file', file);

        const response = await this.request('/upload/v2', {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Erreur lors de l\'upload');
        }
        return response.json();
    },

    // =========================================================================
    // PREFERENCES
    // =========================================================================

    /**
     * Recupere les preferences de l'utilisateur
     * @returns {Promise<object>}
     */
    async getPreferences() {
        const response = await this.request('/preferences/');
        if (!response.ok) throw new Error('Erreur lors du chargement des preferences');
        return response.json();
    },

    /**
     * Met a jour les preferences
     * @param {object} data
     * @returns {Promise<object>}
     */
    async updatePreferences(data) {
        const response = await this.request('/preferences/', {
            method: 'PATCH',
            body: JSON.stringify(data)
        });
        if (!response.ok) throw new Error('Erreur lors de la mise a jour des preferences');
        return response.json();
    },

    // =========================================================================
    // PROFILE
    // =========================================================================

    /**
     * Recupere le profil complet de l'utilisateur
     * @returns {Promise<object>}
     */
    async getProfile() {
        const response = await this.request('/users/me/profile');
        if (!response.ok) throw new Error('Erreur lors du chargement du profil');
        return response.json();
    },

    /**
     * Met a jour le profil utilisateur
     * @param {object} data - {first_name, last_name, phone, address_line1, address_line2, city_id, country_code}
     * @returns {Promise<object>}
     */
    async updateProfile(data) {
        const response = await this.request('/users/me/profile', {
            method: 'PATCH',
            body: JSON.stringify(data)
        });
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Erreur lors de la mise a jour du profil');
        }
        return response.json();
    },

    /**
     * Change le mot de passe de l'utilisateur
     * @param {string} currentPassword
     * @param {string} newPassword
     * @param {string} confirmPassword
     * @returns {Promise<object>}
     */
    async changePassword(currentPassword, newPassword, confirmPassword) {
        const response = await this.request('/users/me/change-password', {
            method: 'POST',
            body: JSON.stringify({
                current_password: currentPassword,
                new_password: newPassword,
                confirm_password: confirmPassword
            })
        });
        if (!response.ok) {
            const error = await response.json();
            // Gerer les erreurs de validation de politique
            if (typeof error.detail === 'object' && error.detail.errors) {
                throw new Error(error.detail.errors.join(', '));
            }
            throw new Error(error.detail || 'Erreur lors du changement de mot de passe');
        }
        return response.json();
    },

    // =========================================================================
    // GEO - Pays et Villes
    // =========================================================================

    /**
     * Recupere la liste des pays actifs
     * @returns {Promise<Array>}
     */
    async getCountries() {
        const response = await this.request('/geo/countries');
        if (!response.ok) throw new Error('Erreur lors du chargement des pays');
        return response.json();
    },

    /**
     * Recherche des villes par terme
     * @param {string} query - Terme de recherche (min 2 chars)
     * @param {string} countryCode - Code pays optionnel
     * @param {number} limit - Nombre max de resultats
     * @returns {Promise<Array>}
     */
    async searchCities(query, countryCode = 'FR', limit = 20) {
        const params = new URLSearchParams({
            q: query,
            country: countryCode,
            limit: limit.toString()
        });

        const response = await this.request(`/geo/cities?${params.toString()}`);
        if (!response.ok) throw new Error('Erreur lors de la recherche de villes');
        return response.json();
    }
};

// Export pour utilisation globale
window.ApiService = ApiService;
