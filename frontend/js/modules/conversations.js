/**
 * Conversations Module
 *
 * Gestion des conversations (CRUD, affichage, navigation)
 */

/**
 * Charge les conversations depuis le backend
 */
async function loadConversationsFromBackend() {
    try {
        const response = await ApiService.listConversations();
        window.conversations = response.items.map(conv => ({
            id: conv.id,
            title: conv.title,
            modeId: conv.mode_id,
            modeName: conv.mode_name,
            messagesCount: conv.messages_count,
            createdAt: conv.created_at,
            updatedAt: conv.updated_at,
            archivedAt: conv.archived_at,
            messages: []
        }));

        renderConversations();

        // Charger la premiere conversation active
        const activeConvs = window.conversations.filter(c => !c.archivedAt);
        if (activeConvs.length > 0) {
            loadConversation(activeConvs[0].id);
        } else {
            await createNewConversation();
        }

    } catch (error) {
        console.error('Error loading conversations:', error);
    }
}

/**
 * Affiche la liste des conversations
 */
function renderConversations() {
    const list = document.getElementById('conversationsList');
    list.innerHTML = '';

    const activeConversations = window.conversations.filter(c => !c.archivedAt);
    const archivedConversations = window.conversations.filter(c => c.archivedAt);

    // Conversations actives
    activeConversations.forEach(conv => {
        list.appendChild(createConversationItem(conv));
    });

    // Conversations archivees
    if (archivedConversations.length > 0) {
        const separator = document.createElement('div');
        separator.className = 'conversations-separator';
        separator.innerHTML = `<span>Archives (${archivedConversations.length})</span>`;
        list.appendChild(separator);

        archivedConversations.forEach(conv => {
            list.appendChild(createConversationItem(conv, true));
        });
    }
}

/**
 * Cree un element de conversation pour la liste
 * @param {Object} conv - Conversation
 * @param {boolean} isArchived - Est archivee
 * @returns {HTMLElement}
 */
function createConversationItem(conv, isArchived = false) {
    const item = document.createElement('div');
    item.className = `conversation-item ${conv.id === window.currentConversationId ? 'active' : ''} ${isArchived ? 'archived' : ''}`;

    const archiveBtn = isArchived ? `
        <button class="btn-conv-action btn-unarchive" data-id="${conv.id}" title="Desarchiver">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polyline points="1 4 1 10 7 10"/>
                <path d="M3.51 15a9 9 0 1 0 2.13-9.36L1 10"/>
            </svg>
        </button>
    ` : `
        <button class="btn-conv-action btn-archive" data-id="${conv.id}" title="Archiver">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polyline points="21 8 21 21 3 21 3 8"/>
                <rect x="1" y="3" width="22" height="5"/>
                <line x1="10" y1="12" x2="14" y2="12"/>
            </svg>
        </button>
    `;

    item.innerHTML = `
        <div class="conversation-info">
            <div class="conversation-title">${escapeHtml(conv.title)}</div>
            <div class="conversation-date">${formatDate(conv.updatedAt)}</div>
        </div>
        <div class="conversation-actions">
            ${archiveBtn}
            <button class="btn-conv-action btn-delete-conversation" data-id="${conv.id}" title="Supprimer">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M3 6h18M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2"/>
                </svg>
            </button>
        </div>
    `;

    // Click sur conversation
    item.addEventListener('click', (e) => {
        if (window.DEBUG) console.log('[Conversations] Clicked:', conv.id, conv.title);
        if (!e.target.closest('.btn-conv-action')) {
            loadConversation(conv.id);
        }
    });

    // Bouton supprimer
    item.querySelector('.btn-delete-conversation').addEventListener('click', (e) => {
        e.stopPropagation();
        deleteConversation(conv.id);
    });

    // Bouton archiver
    const archiveBtnEl = item.querySelector('.btn-archive');
    if (archiveBtnEl) {
        archiveBtnEl.addEventListener('click', (e) => {
            e.stopPropagation();
            archiveConversation(conv.id);
        });
    }

    // Bouton desarchiver
    const unarchiveBtnEl = item.querySelector('.btn-unarchive');
    if (unarchiveBtnEl) {
        unarchiveBtnEl.addEventListener('click', (e) => {
            e.stopPropagation();
            unarchiveConversation(conv.id);
        });
    }

    return item;
}

/**
 * Archive une conversation
 * @param {string} id - ID de la conversation
 */
async function archiveConversation(id) {
    try {
        await ApiService.archiveConversation(id);
        const conv = window.conversations.find(c => c.id === id);
        if (conv) {
            conv.archivedAt = new Date().toISOString();
        }
        renderConversations();

        if (window.currentConversationId === id) {
            const activeConvs = window.conversations.filter(c => !c.archivedAt);
            if (activeConvs.length > 0) {
                loadConversation(activeConvs[0].id);
            } else {
                await createNewConversation();
            }
        }
    } catch (error) {
        console.error('Error archiving conversation:', error);
        showToast('Erreur lors de l\'archivage', 'error');
    }
}

/**
 * Desarchive une conversation
 * @param {string} id - ID de la conversation
 */
async function unarchiveConversation(id) {
    try {
        await ApiService.unarchiveConversation(id);
        const conv = window.conversations.find(c => c.id === id);
        if (conv) {
            conv.archivedAt = null;
        }
        renderConversations();
    } catch (error) {
        console.error('Error unarchiving conversation:', error);
        showToast('Erreur lors du desarchivage', 'error');
    }
}

/**
 * Cree une nouvelle conversation
 */
async function createNewConversation() {
    try {
        const modeId = window.CONFIG.mode === 'assistant' ? 2 : 1;
        const result = await ApiService.createConversation('Nouvelle conversation', modeId);

        const conversation = {
            id: result.id,
            title: result.title,
            modeId: result.mode_id,
            modeName: result.mode_name,
            messagesCount: 0,
            createdAt: result.created_at,
            updatedAt: result.updated_at,
            messages: []
        };

        window.conversations.unshift(conversation);
        renderConversations();
        loadConversation(conversation.id);

    } catch (error) {
        console.error('Error creating conversation:', error);
        showToast('Erreur lors de la creation de la conversation', 'error');
    }
}

/**
 * Charge une conversation
 * @param {string} id - ID de la conversation
 */
async function loadConversation(id) {
    if (window.DEBUG) console.log('[Conversations] Loading:', id);

    window.currentConversationId = id;
    const conversation = window.conversations.find(c => c.id === id);

    if (!conversation) {
        if (window.DEBUG) console.log('[Conversations] Not found in local list');
        return;
    }

    document.getElementById('chatTitle').textContent = conversation.title;
    document.getElementById('chatMode').textContent = conversation.modeName || 'ChatBot';

    const container = document.getElementById('messagesContainer');

    try {
        const detail = await ApiService.getConversation(id);
        conversation.messages = detail.messages || [];

        if (conversation.messages.length === 0) {
            showWelcomeMessage();
        } else {
            container.innerHTML = '';
            conversation.messages.forEach(msg => {
                appendMessage(
                    msg.sender_type === 'user' ? 'user' : 'assistant',
                    msg.content,
                    msg.created_at,
                    msg.sources,
                    false,
                    msg.id
                );
            });
        }

    } catch (error) {
        console.error('[Conversations] Error loading:', error);
        showWelcomeMessage();
    }

    renderConversations();
    scrollToBottom();
}

/**
 * Affiche le message de bienvenue
 */
function showWelcomeMessage() {
    const container = document.getElementById('messagesContainer');
    container.innerHTML = `
        <div class="welcome-message">
            <h2>👋 Bienvenue sur MY-IA</h2>
            <p>Posez-moi vos questions, je suis là pour vous aider avec vos documents et données indexées.</p>
            <div class="suggestions">
                <button class="suggestion-btn" data-query="Explique-moi comment fonctionne le RAG">Comment fonctionne le RAG ?</button>
                <button class="suggestion-btn" data-query="Quels sont les fichiers disponibles dans la base de connaissances ?">Quels fichiers sont disponibles ?</button>
                <button class="suggestion-btn" data-query="Comment puis-je ajouter de nouveaux documents ?">Ajouter des documents</button>
            </div>
        </div>
    `;

    container.querySelectorAll('.suggestion-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.getElementById('messageInput').value = btn.dataset.query;
            sendMessage();
        });
    });
}

/**
 * Supprime une conversation
 * @param {string} id - ID de la conversation
 */
async function deleteConversation(id) {
    const confirmed = await showConfirm({
        title: 'Supprimer la conversation',
        message: 'Cette action est irreversible. Voulez-vous vraiment supprimer cette conversation ?',
        confirmText: 'Supprimer',
        cancelText: 'Annuler',
        type: 'danger'
    });
    if (!confirmed) return;

    try {
        await ApiService.deleteConversation(id);

        window.conversations = window.conversations.filter(c => c.id !== id);

        if (window.currentConversationId === id) {
            if (window.conversations.length > 0) {
                loadConversation(window.conversations[0].id);
            } else {
                await createNewConversation();
            }
        }

        renderConversations();

    } catch (error) {
        console.error('Error deleting conversation:', error);
        showToast('Erreur lors de la suppression de la conversation', 'error');
    }
}

/**
 * Met a jour le titre de la conversation
 * @param {string} content - Contenu du premier message
 */
async function updateConversationTitle(content) {
    const conversation = window.conversations.find(c => c.id === window.currentConversationId);
    if (!conversation || conversation.messagesCount > 0) return;

    const newTitle = content.substring(0, 50) + (content.length > 50 ? '...' : '');

    try {
        await ApiService.updateConversation(window.currentConversationId, { title: newTitle });
        conversation.title = newTitle;
        document.getElementById('chatTitle').textContent = newTitle;
        renderConversations();
    } catch (error) {
        console.error('Error updating title:', error);
    }
}

// Export global
window.ConversationsModule = {
    loadFromBackend: loadConversationsFromBackend,
    render: renderConversations,
    createNew: createNewConversation,
    load: loadConversation,
    delete: deleteConversation,
    archive: archiveConversation,
    unarchive: unarchiveConversation,
    updateTitle: updateConversationTitle,
    showWelcome: showWelcomeMessage
};

// Exports individuels pour compatibilite
window.loadConversationsFromBackend = loadConversationsFromBackend;
window.renderConversations = renderConversations;
window.createNewConversation = createNewConversation;
window.loadConversation = loadConversation;
window.deleteConversation = deleteConversation;
window.archiveConversation = archiveConversation;
window.unarchiveConversation = unarchiveConversation;
window.updateConversationTitle = updateConversationTitle;
window.showWelcomeMessage = showWelcomeMessage;
