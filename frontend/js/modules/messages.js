/**
 * Messages Module
 *
 * Affichage, edition et gestion des messages
 */

/**
 * Ajoute un message au container
 * @param {string} role - 'user' ou 'assistant'
 * @param {string} content - Contenu du message
 * @param {string} timestamp - Date ISO
 * @param {Array|null} sources - Sources utilisees
 * @param {boolean} saveScroll - Scroll vers le bas
 * @param {string|null} messageId - ID du message
 */
function appendMessage(role, content, timestamp, sources = null, saveScroll = true, messageId = null) {
    const messageDiv = createMessageElement(role, content, timestamp, sources, messageId);
    document.getElementById('messagesContainer').appendChild(messageDiv);

    if (saveScroll) {
        scrollToBottom();
    }
}

/**
 * Cree un element de message
 * @param {string} role - 'user' ou 'assistant'
 * @param {string} content - Contenu du message
 * @param {string} timestamp - Date ISO
 * @param {Array|null} sources - Sources
 * @param {string|null} messageId - ID
 * @returns {HTMLElement}
 */
function createMessageElement(role, content, timestamp, sources = null, messageId = null) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${role}`;
    messageDiv.dataset.content = content;
    if (messageId) {
        messageDiv.dataset.messageId = messageId;
    }

    const avatar = role === 'user' ? 'U' : 'IA';
    const author = role === 'user' ? 'Vous' : 'Assistant';

    let sourcesHtml = '';
    if (sources && sources.length > 0 && window.CONFIG.showSources) {
        sourcesHtml = `
            <div class="message-sources">
                <h4>Sources utilisees:</h4>
                ${sources.map(s => `<div class="source-item">- ${escapeHtml(s.source || s)}</div>`).join('')}
            </div>
        `;
    }

    // Boutons specifiques
    const editBtn = role === 'user' ? `
        <button class="btn-icon btn-edit" data-tooltip="Modifier ce message">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
                <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
            </svg>
        </button>
    ` : '';

    const regenerateBtn = role === 'assistant' ? `
        <button class="btn-icon btn-regenerate" data-tooltip="Regenerer la reponse">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polyline points="23 4 23 10 17 10"/>
                <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/>
            </svg>
        </button>
    ` : '';

    const deleteBtn = role === 'user' ? `
        <button class="btn-icon btn-delete-msg" data-tooltip="Supprimer ce message et sa reponse">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M3 6h18M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2"/>
                <line x1="10" y1="11" x2="10" y2="17"/>
                <line x1="14" y1="11" x2="14" y2="17"/>
            </svg>
        </button>
    ` : '';

    messageDiv.innerHTML = `
        <div class="message-avatar">${avatar}</div>
        <div class="message-content">
            <div class="message-header">
                <span class="message-author">${author}</span>
                <span class="message-time">${formatTime(timestamp)}</span>
            </div>
            <div class="message-text">${marked.parse(content)}</div>
            ${sourcesHtml}
            <div class="message-actions">
                <button class="btn-icon btn-copy" data-tooltip="Copier le texte">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <rect x="9" y="9" width="13" height="13" rx="2" ry="2"/>
                        <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>
                    </svg>
                </button>
                ${editBtn}
                ${regenerateBtn}
                ${deleteBtn}
            </div>
        </div>
    `;

    // Event: Copier
    setupCopyButton(messageDiv, content);

    // Event: Editer
    if (role === 'user') {
        messageDiv.querySelector('.btn-edit').addEventListener('click', () => {
            editMessage(messageDiv, content);
        });
    }

    // Event: Regenerer
    if (role === 'assistant') {
        messageDiv.querySelector('.btn-regenerate').addEventListener('click', () => {
            regenerateResponse(messageDiv);
        });
    }

    // Event: Supprimer
    if (role === 'user') {
        const deleteBtnEl = messageDiv.querySelector('.btn-delete-msg');
        if (deleteBtnEl) {
            deleteBtnEl.addEventListener('click', () => {
                deleteMessagePair(messageDiv);
            });
        }
    }

    return messageDiv;
}

/**
 * Configure le bouton copier
 * @param {HTMLElement} messageDiv - Element message
 * @param {string} content - Contenu a copier
 */
function setupCopyButton(messageDiv, content) {
    const copyBtn = messageDiv.querySelector('.btn-copy');
    copyBtn.addEventListener('click', () => {
        navigator.clipboard.writeText(content);
        copyBtn.classList.add('copied');
        copyBtn.dataset.tooltip = 'Copie !';
        copyBtn.innerHTML = `
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polyline points="20 6 9 17 4 12"/>
            </svg>
        `;
        setTimeout(() => {
            copyBtn.classList.remove('copied');
            copyBtn.dataset.tooltip = 'Copier le texte';
            copyBtn.innerHTML = `
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <rect x="9" y="9" width="13" height="13" rx="2" ry="2"/>
                    <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>
                </svg>
            `;
        }, 2000);
    });
}

/**
 * Supprime un message et sa reponse
 * @param {HTMLElement} messageDiv - Element message utilisateur
 */
async function deleteMessagePair(messageDiv) {
    const container = document.getElementById('messagesContainer');
    const messages = Array.from(container.querySelectorAll('.message'));
    const currentIndex = messages.indexOf(messageDiv);

    let messagesToDelete = [messageDiv];
    let confirmMessage = 'Supprimer ce message ?';

    // Verifier s'il y a une reponse apres
    const nextMessage = messages[currentIndex + 1];
    if (nextMessage && nextMessage.classList.contains('assistant')) {
        messagesToDelete.push(nextMessage);
        confirmMessage = 'Supprimer cette question et sa reponse ?';
    }

    const confirmed = await showConfirm({
        title: 'Supprimer le message',
        message: confirmMessage,
        confirmText: 'Supprimer',
        cancelText: 'Annuler',
        type: 'danger'
    });
    if (!confirmed) return;

    // IDs a supprimer
    const messageIds = messagesToDelete
        .map(m => m.dataset.messageId)
        .filter(id => id);

    // Appel API
    if (messageIds.length > 0 && window.currentConversationId) {
        try {
            await ApiService.deleteMessages(window.currentConversationId, messageIds);
            if (window.DEBUG) console.log('[Messages] Soft-deleted:', messageIds);
        } catch (error) {
            console.error('[Messages] Error deleting:', error);
            showToast('Erreur lors de la suppression des messages', 'error');
            return;
        }
    }

    // Supprimer du DOM
    messagesToDelete.forEach(msg => msg.remove());

    // Mettre a jour la conversation locale
    const conversation = window.conversations.find(c => c.id === window.currentConversationId);
    if (conversation && conversation.messages) {
        const deletedIds = messagesToDelete.map(m => m.dataset.messageId).filter(id => id);
        const deletedContents = messagesToDelete.map(m => m.dataset.content);
        conversation.messages = conversation.messages.filter(
            msg => !deletedIds.includes(msg.id) && !deletedContents.includes(msg.content)
        );
        conversation.messagesCount = conversation.messages.length;
    }

    // Message de bienvenue si vide
    if (container.querySelectorAll('.message').length === 0) {
        showWelcomeMessage();
    }
}

/**
 * Edite un message utilisateur
 * @param {HTMLElement} messageDiv - Element message
 * @param {string} originalContent - Contenu original
 */
function editMessage(messageDiv, originalContent) {
    const contentDiv = messageDiv.querySelector('.message-content');
    const textDiv = messageDiv.querySelector('.message-text');
    const actionsDiv = messageDiv.querySelector('.message-actions');

    // Container d'edition
    const editContainer = document.createElement('div');
    editContainer.className = 'message-edit-container';

    const textarea = document.createElement('textarea');
    textarea.className = 'message-edit-textarea';
    textarea.value = originalContent;
    textarea.rows = Math.max(3, originalContent.split('\n').length);

    const editActions = document.createElement('div');
    editActions.className = 'message-edit-actions';
    editActions.innerHTML = `
        <button class="btn-action btn-save">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M22 2L11 13"/>
                <path d="M22 2L15 22L11 13L2 9L22 2Z"/>
            </svg>
            Envoyer
        </button>
        <button class="btn-action btn-cancel">Annuler</button>
    `;

    editContainer.appendChild(textarea);
    editContainer.appendChild(editActions);

    textDiv.style.display = 'none';
    actionsDiv.style.display = 'none';
    contentDiv.appendChild(editContainer);

    textarea.focus();
    textarea.setSelectionRange(textarea.value.length, textarea.value.length);

    // Auto-resize
    textarea.addEventListener('input', () => {
        textarea.style.height = 'auto';
        textarea.style.height = textarea.scrollHeight + 'px';
    });

    // Annuler
    editActions.querySelector('.btn-cancel').addEventListener('click', () => {
        editContainer.remove();
        textDiv.style.display = 'block';
        actionsDiv.style.display = 'flex';
    });

    // Envoyer
    editActions.querySelector('.btn-save').addEventListener('click', async () => {
        const newContent = textarea.value.trim();
        if (!newContent) return;

        editContainer.remove();

        // Supprimer les messages suivants
        const container = document.getElementById('messagesContainer');
        let foundMessage = false;
        const messagesToRemove = [];

        Array.from(container.children).forEach(child => {
            if (foundMessage) {
                messagesToRemove.push(child);
            }
            if (child === messageDiv) {
                foundMessage = true;
            }
        });

        messagesToRemove.forEach(msg => msg.remove());

        // Mettre a jour le message
        messageDiv.dataset.content = newContent;
        textDiv.innerHTML = marked.parse(newContent);
        textDiv.style.display = 'block';
        actionsDiv.style.display = 'flex';

        // Envoyer le nouveau message
        const typingId = showTypingIndicator();

        try {
            window.isStreaming = true;
            document.getElementById('sendBtn').style.display = 'none';
            document.getElementById('stopBtn').style.display = 'flex';
            window.abortController = new AbortController();

            await streamMessage(newContent, typingId);

        } catch (error) {
            console.error('Error sending edited message:', error);
            removeTypingIndicator(typingId);
            if (error.name !== 'AbortError') {
                appendMessage('assistant', 'Erreur lors de l\'envoi du message modifie.', new Date().toISOString());
            }
        } finally {
            window.isStreaming = false;
            document.getElementById('sendBtn').style.display = 'flex';
            document.getElementById('stopBtn').style.display = 'none';
            window.abortController = null;
        }
    });
}

/**
 * Regenere une reponse assistant
 * @param {HTMLElement} assistantMessageDiv - Element message assistant
 */
async function regenerateResponse(assistantMessageDiv) {
    const container = document.getElementById('messagesContainer');
    const messages = Array.from(container.querySelectorAll('.message'));
    const assistantIndex = messages.indexOf(assistantMessageDiv);

    if (assistantIndex <= 0) return;

    // Chercher le message utilisateur precedent
    let userMessage = null;
    for (let i = assistantIndex - 1; i >= 0; i--) {
        if (messages[i].classList.contains('user')) {
            userMessage = messages[i];
            break;
        }
    }

    if (!userMessage) return;

    const userContent = userMessage.dataset.content;

    // Supprimer la reponse actuelle
    assistantMessageDiv.remove();

    // Regenerer
    const typingId = showTypingIndicator();

    try {
        window.isStreaming = true;
        document.getElementById('sendBtn').style.display = 'none';
        document.getElementById('stopBtn').style.display = 'flex';
        window.abortController = new AbortController();

        await streamMessage(userContent, typingId);

    } catch (error) {
        console.error('Error regenerating:', error);
        removeTypingIndicator(typingId);
        if (error.name !== 'AbortError') {
            appendMessage('assistant', 'Erreur lors de la regeneration.', new Date().toISOString());
        }
    } finally {
        window.isStreaming = false;
        document.getElementById('sendBtn').style.display = 'flex';
        document.getElementById('stopBtn').style.display = 'none';
        window.abortController = null;
    }
}

/**
 * Affiche l'indicateur de frappe
 * @returns {string} ID de l'indicateur
 */
function showTypingIndicator() {
    const id = 'typing-' + Date.now();
    const typingDiv = document.createElement('div');
    typingDiv.id = id;
    typingDiv.className = 'message assistant';
    typingDiv.innerHTML = `
        <div class="message-avatar">IA</div>
        <div class="message-content">
            <div class="typing-indicator">
                <div class="typing-dot"></div>
                <div class="typing-dot"></div>
                <div class="typing-dot"></div>
            </div>
        </div>
    `;
    document.getElementById('messagesContainer').appendChild(typingDiv);
    scrollToBottom();
    return id;
}

/**
 * Retire l'indicateur de frappe
 * @param {string} id - ID de l'indicateur
 */
function removeTypingIndicator(id) {
    const element = document.getElementById(id);
    if (element) {
        element.remove();
    }
}

// Export global
window.MessagesModule = {
    append: appendMessage,
    createElement: createMessageElement,
    delete: deleteMessagePair,
    edit: editMessage,
    regenerate: regenerateResponse,
    showTyping: showTypingIndicator,
    removeTyping: removeTypingIndicator
};

// Exports individuels
window.appendMessage = appendMessage;
window.createMessageElement = createMessageElement;
window.deleteMessagePair = deleteMessagePair;
window.editMessage = editMessage;
window.regenerateResponse = regenerateResponse;
window.showTypingIndicator = showTypingIndicator;
window.removeTypingIndicator = removeTypingIndicator;
