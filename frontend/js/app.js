// Configuration et état global
const CONFIG = {
    apiUrl: localStorage.getItem('apiUrl') || 'http://localhost:8080',
    apiKey: localStorage.getItem('apiKey') || 'change-me-in-production',
    topK: parseInt(localStorage.getItem('topK')) || 4,
    showSources: localStorage.getItem('showSources') === 'true',
    theme: localStorage.getItem('theme') || 'light',
    mode: 'chat' // 'chat' ou 'assistant'
};

let currentConversationId = null;
let conversations = JSON.parse(localStorage.getItem('conversations')) || [];
let isStreaming = false;
let abortController = null;

// Configuration de marked pour le markdown
marked.setOptions({
    highlight: function(code, lang) {
        if (lang && hljs.getLanguage(lang)) {
            return hljs.highlight(code, { language: lang }).value;
        }
        return hljs.highlightAuto(code).value;
    },
    breaks: true,
    gfm: true
});

// Initialisation
document.addEventListener('DOMContentLoaded', () => {
    initializeTheme();
    initializeEventListeners();
    loadConversations();
    loadSettings();

    // Créer une nouvelle conversation par défaut si aucune n'existe
    if (conversations.length === 0) {
        createNewConversation();
    } else {
        loadConversation(conversations[0].id);
    }
});

// Gestion du thème
function initializeTheme() {
    document.documentElement.setAttribute('data-theme', CONFIG.theme);
}

function toggleTheme() {
    CONFIG.theme = CONFIG.theme === 'light' ? 'dark' : 'light';
    localStorage.setItem('theme', CONFIG.theme);
    document.documentElement.setAttribute('data-theme', CONFIG.theme);
}

// Event Listeners
function initializeEventListeners() {
    // Toggle sidebar
    document.getElementById('toggleSidebar').addEventListener('click', () => {
        document.getElementById('sidebar').classList.toggle('hidden');
    });

    // Nouvelle conversation
    document.getElementById('newChatBtn').addEventListener('click', createNewConversation);

    // Toggle theme
    document.getElementById('themeToggle').addEventListener('click', toggleTheme);

    // Paramètres
    document.getElementById('settingsBtn').addEventListener('click', () => {
        document.getElementById('settingsPanel').classList.add('open');
        document.getElementById('settingsPanel').style.display = 'block';
    });

    document.getElementById('closeSettings').addEventListener('click', () => {
        document.getElementById('settingsPanel').classList.remove('open');
        setTimeout(() => {
            document.getElementById('settingsPanel').style.display = 'none';
        }, 300);
    });

    document.getElementById('saveSettings').addEventListener('click', saveSettings);

    // Mode toggle
    document.getElementById('modeToggle').addEventListener('change', (e) => {
        CONFIG.mode = e.target.checked ? 'assistant' : 'chat';
        document.getElementById('chatMode').textContent = e.target.checked ? 'Assistant' : 'ChatBot';
    });

    // Formulaire de chat
    const chatForm = document.getElementById('chatForm');
    const messageInput = document.getElementById('messageInput');

    chatForm.addEventListener('submit', (e) => {
        e.preventDefault();
        sendMessage();
    });

    // Auto-resize textarea
    messageInput.addEventListener('input', (e) => {
        e.target.style.height = 'auto';
        e.target.style.height = e.target.scrollHeight + 'px';
        document.getElementById('charCount').textContent = `${e.target.value.length} caractères`;
    });

    // Shift + Enter pour nouvelle ligne, Enter seul pour envoyer
    messageInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    // Suggestions
    document.querySelectorAll('.suggestion-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            messageInput.value = btn.dataset.query;
            sendMessage();
        });
    });

    // Stop generation
    document.getElementById('stopBtn').addEventListener('click', stopGeneration);

    // Aide sur les modes
    const modeHelpBtn = document.getElementById('modeHelpBtn');
    const modeHelpTooltip = document.getElementById('modeHelpTooltip');

    modeHelpBtn.addEventListener('click', (e) => {
        e.preventDefault();
        e.stopPropagation();

        const isVisible = modeHelpTooltip.style.display === 'block';
        modeHelpTooltip.style.display = isVisible ? 'none' : 'block';
    });

    // Fermer le tooltip en cliquant ailleurs
    document.addEventListener('click', (e) => {
        if (!e.target.closest('.mode-toggle') && !e.target.closest('.mode-help-tooltip')) {
            modeHelpTooltip.style.display = 'none';
        }
    });
}

// Gestion des conversations
function createNewConversation() {
    const conversation = {
        id: Date.now().toString(),
        title: 'Nouvelle conversation',
        messages: [],
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString()
    };

    conversations.unshift(conversation);
    saveConversationsToStorage();
    loadConversations();
    loadConversation(conversation.id);

    // Masquer le message de bienvenue
    document.querySelector('.welcome-message')?.remove();
}

function loadConversations() {
    const list = document.getElementById('conversationsList');
    list.innerHTML = '';

    conversations.forEach(conv => {
        const item = document.createElement('div');
        item.className = `conversation-item ${conv.id === currentConversationId ? 'active' : ''}`;
        item.innerHTML = `
            <div>
                <div class="conversation-title">${escapeHtml(conv.title)}</div>
                <div class="conversation-date">${formatDate(conv.updatedAt)}</div>
            </div>
            <button class="btn-delete-conversation" data-id="${conv.id}">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M3 6h18M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2"/>
                </svg>
            </button>
        `;

        item.addEventListener('click', (e) => {
            if (!e.target.closest('.btn-delete-conversation')) {
                loadConversation(conv.id);
            }
        });

        const deleteBtn = item.querySelector('.btn-delete-conversation');
        deleteBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            deleteConversation(conv.id);
        });

        list.appendChild(item);
    });
}

function loadConversation(id) {
    currentConversationId = id;
    const conversation = conversations.find(c => c.id === id);

    if (!conversation) return;

    document.getElementById('chatTitle').textContent = conversation.title;

    const container = document.getElementById('messagesContainer');
    container.innerHTML = '';

    conversation.messages.forEach(msg => {
        appendMessage(msg.role, msg.content, msg.timestamp, msg.sources, false);
    });

    loadConversations(); // Refresh list to update active state
    scrollToBottom();
}

function deleteConversation(id) {
    if (!confirm('Êtes-vous sûr de vouloir supprimer cette conversation ?')) return;

    conversations = conversations.filter(c => c.id !== id);
    saveConversationsToStorage();

    if (currentConversationId === id) {
        if (conversations.length > 0) {
            loadConversation(conversations[0].id);
        } else {
            createNewConversation();
        }
    }

    loadConversations();
}

function updateConversationTitle(content) {
    const conversation = conversations.find(c => c.id === currentConversationId);
    if (!conversation || conversation.messages.length > 1) return;

    // Utiliser les premiers mots du message comme titre
    conversation.title = content.substring(0, 50) + (content.length > 50 ? '...' : '');
    conversation.updatedAt = new Date().toISOString();
    saveConversationsToStorage();
    loadConversations();
}

function saveConversationsToStorage() {
    localStorage.setItem('conversations', JSON.stringify(conversations));
}

// Envoi et réception de messages
async function sendMessage() {
    const input = document.getElementById('messageInput');
    const message = input.value.trim();

    if (!message || isStreaming) return;

    // Ajouter le message de l'utilisateur
    appendMessage('user', message, new Date().toISOString());

    // Sauvegarder dans la conversation
    const conversation = conversations.find(c => c.id === currentConversationId);
    conversation.messages.push({
        role: 'user',
        content: message,
        timestamp: new Date().toISOString()
    });

    // Mettre à jour le titre si c'est le premier message
    updateConversationTitle(message);

    // Réinitialiser l'input
    input.value = '';
    input.style.height = 'auto';
    document.getElementById('charCount').textContent = '0 caractères';

    // Afficher l'indicateur de frappe
    const typingId = showTypingIndicator();

    try {
        isStreaming = true;
        document.getElementById('sendBtn').style.display = 'none';
        document.getElementById('stopBtn').style.display = 'flex';

        abortController = new AbortController();

        const endpoint = CONFIG.mode === 'assistant' ? '/assistant' : '/chat';
        const useStreaming = true; // Toujours utiliser le streaming pour une meilleure UX

        if (useStreaming) {
            await streamMessage(message, typingId);
        } else {
            await fetchMessage(message, typingId);
        }

    } catch (error) {
        console.error('Error sending message:', error);
        removeTypingIndicator(typingId);

        if (error.name !== 'AbortError') {
            appendMessage('assistant', '❌ Désolé, une erreur est survenue. Vérifiez que l\'API est accessible et réessayez.', new Date().toISOString());
        }
    } finally {
        isStreaming = false;
        document.getElementById('sendBtn').style.display = 'flex';
        document.getElementById('stopBtn').style.display = 'none';
        abortController = null;
    }
}

async function streamMessage(message, typingId) {
    console.log('[STREAM] Starting stream request');

    const response = await fetch(`${CONFIG.apiUrl}/chat/stream`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-API-Key': CONFIG.apiKey
        },
        body: JSON.stringify({
            query: message,
            session_id: currentConversationId
        }),
        signal: abortController.signal
    });

    console.log('[STREAM] Response status:', response.status);

    if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
    }

    removeTypingIndicator(typingId);

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let assistantMessageDiv = null;
    let fullResponse = '';
    let buffer = ''; // Buffer pour gérer les chunks partiels

    console.log('[STREAM] Starting to read chunks');

    while (true) {
        const { done, value } = await reader.read();

        if (done) {
            console.log('[STREAM] Stream completed');
            break;
        }

        const chunk = decoder.decode(value, { stream: true });
        buffer += chunk;

        // Séparer par lignes complètes
        const lines = buffer.split('\n');
        // Garder la dernière partie (potentiellement incomplète) dans le buffer
        buffer = lines.pop() || '';

        for (const line of lines) {
            if (!line.trim()) continue;

            try {
                const data = JSON.parse(line);
                console.log('[STREAM] Parsed data:', { response: data.response, done: data.done });

                if (data.response) {
                    fullResponse += data.response;

                    if (!assistantMessageDiv) {
                        assistantMessageDiv = createMessageElement('assistant', '', new Date().toISOString());
                        // IMPORTANT: Ajouter l'élément au DOM!
                        document.getElementById('messagesContainer').appendChild(assistantMessageDiv);
                        console.log('[STREAM] Created and appended message element');
                    }

                    // Mettre à jour le contenu avec le markdown rendu
                    const contentDiv = assistantMessageDiv.querySelector('.message-text');
                    if (typeof marked !== 'undefined' && marked.parse) {
                        contentDiv.innerHTML = marked.parse(fullResponse);
                    } else {
                        // Fallback si marked n'est pas disponible
                        contentDiv.textContent = fullResponse;
                    }
                    scrollToBottom();
                }

                if (data.done) {
                    console.log('[STREAM] Message completed');
                    // Message terminé
                    const conversation = conversations.find(c => c.id === currentConversationId);
                    conversation.messages.push({
                        role: 'assistant',
                        content: fullResponse,
                        timestamp: new Date().toISOString()
                    });
                    conversation.updatedAt = new Date().toISOString();
                    saveConversationsToStorage();
                }
            } catch (e) {
                console.error('[STREAM] Error parsing JSON:', e.message);
                console.error('[STREAM] Problematic line (first 200 chars):', line.substring(0, 200));
            }
        }
    }

    // Traiter le dernier morceau du buffer s'il reste quelque chose
    if (buffer.trim()) {
        try {
            const data = JSON.parse(buffer);
            if (data.done) {
                console.log('[STREAM] Final message completed');
                const conversation = conversations.find(c => c.id === currentConversationId);
                if (!conversation.messages.find(m => m.content === fullResponse)) {
                    conversation.messages.push({
                        role: 'assistant',
                        content: fullResponse,
                        timestamp: new Date().toISOString()
                    });
                    conversation.updatedAt = new Date().toISOString();
                    saveConversationsToStorage();
                }
            }
        } catch (e) {
            console.error('[STREAM] Error parsing final buffer:', e.message);
        }
    }
}

async function fetchMessage(message, typingId) {
    const endpoint = CONFIG.mode === 'assistant' ? '/assistant' : '/chat';

    const response = await fetch(`${CONFIG.apiUrl}${endpoint}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-API-Key': CONFIG.apiKey
        },
        body: JSON.stringify({
            query: message,
            session_id: currentConversationId
        }),
        signal: abortController.signal
    });

    if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
    }

    const data = await response.json();
    removeTypingIndicator(typingId);

    appendMessage('assistant', data.response, new Date().toISOString(), data.sources);

    // Sauvegarder la réponse
    const conversation = conversations.find(c => c.id === currentConversationId);
    conversation.messages.push({
        role: 'assistant',
        content: data.response,
        timestamp: new Date().toISOString(),
        sources: data.sources
    });
    conversation.updatedAt = new Date().toISOString();
    saveConversationsToStorage();
}

function stopGeneration() {
    if (abortController) {
        abortController.abort();
        isStreaming = false;
        document.getElementById('sendBtn').style.display = 'flex';
        document.getElementById('stopBtn').style.display = 'none';
    }
}

// Affichage des messages
function appendMessage(role, content, timestamp, sources = null, saveScroll = true) {
    const messageDiv = createMessageElement(role, content, timestamp, sources);
    document.getElementById('messagesContainer').appendChild(messageDiv);

    if (saveScroll) {
        scrollToBottom();
    }
}

function createMessageElement(role, content, timestamp, sources = null) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${role}`;

    const avatar = role === 'user' ? 'U' : 'IA';
    const author = role === 'user' ? 'Vous' : 'Assistant';

    let sourcesHtml = '';
    if (sources && sources.length > 0 && CONFIG.showSources) {
        sourcesHtml = `
            <div class="message-sources">
                <h4>📚 Sources utilisées:</h4>
                ${sources.map(s => `<div class="source-item">• ${escapeHtml(s.source)}</div>`).join('')}
            </div>
        `;
    }

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
                <button class="btn-action btn-copy" data-content="${escapeHtml(content)}">
                    📋 Copier
                </button>
                ${role === 'assistant' ? '<button class="btn-action btn-regenerate">🔄 Régénérer</button>' : ''}
                ${role === 'user' ? '<button class="btn-action btn-edit">✏️ Éditer</button>' : ''}
            </div>
        </div>
    `;

    // Event listeners pour les actions
    const copyBtn = messageDiv.querySelector('.btn-copy');
    copyBtn.addEventListener('click', () => {
        navigator.clipboard.writeText(content);
        copyBtn.textContent = '✓ Copié';
        setTimeout(() => {
            copyBtn.textContent = '📋 Copier';
        }, 2000);
    });

    const regenerateBtn = messageDiv.querySelector('.btn-regenerate');
    if (regenerateBtn) {
        regenerateBtn.addEventListener('click', () => {
            regenerateResponse(messageDiv);
        });
    }

    const editBtn = messageDiv.querySelector('.btn-edit');
    if (editBtn) {
        editBtn.addEventListener('click', () => {
            editMessage(messageDiv, content);
        });
    }

    return messageDiv;
}

function editMessage(userMessageDiv, originalContent) {
    if (isStreaming) {
        return; // Ne pas éditer pendant un streaming
    }

    const messageTextDiv = userMessageDiv.querySelector('.message-text');
    const actionsDiv = userMessageDiv.querySelector('.message-actions');

    // Créer le champ d'édition
    const editContainer = document.createElement('div');
    editContainer.className = 'message-edit-container';
    editContainer.innerHTML = `
        <textarea class="message-edit-textarea" rows="3">${originalContent}</textarea>
        <div class="message-edit-actions">
            <button class="btn-action btn-save">✓ Enregistrer</button>
            <button class="btn-action btn-cancel">✗ Annuler</button>
        </div>
    `;

    // Cacher le texte original et les actions
    messageTextDiv.style.display = 'none';
    actionsDiv.style.display = 'none';

    // Insérer le champ d'édition
    messageTextDiv.parentNode.insertBefore(editContainer, messageTextDiv.nextSibling);

    const textarea = editContainer.querySelector('.message-edit-textarea');
    const saveBtn = editContainer.querySelector('.btn-save');
    const cancelBtn = editContainer.querySelector('.btn-cancel');

    // Focus et sélection
    textarea.focus();
    textarea.setSelectionRange(textarea.value.length, textarea.value.length);

    // Auto-resize du textarea
    textarea.style.height = 'auto';
    textarea.style.height = textarea.scrollHeight + 'px';
    textarea.addEventListener('input', (e) => {
        e.target.style.height = 'auto';
        e.target.style.height = e.target.scrollHeight + 'px';
    });

    // Annuler
    cancelBtn.addEventListener('click', () => {
        editContainer.remove();
        messageTextDiv.style.display = '';
        actionsDiv.style.display = '';
    });

    // Enregistrer
    saveBtn.addEventListener('click', async () => {
        const newContent = textarea.value.trim();
        if (!newContent || newContent === originalContent) {
            // Pas de changement, annuler
            cancelBtn.click();
            return;
        }

        await saveAndResendMessage(userMessageDiv, newContent);
    });

    // Enter pour enregistrer (Shift+Enter pour nouvelle ligne)
    textarea.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            saveBtn.click();
        }
        if (e.key === 'Escape') {
            cancelBtn.click();
        }
    });
}

async function saveAndResendMessage(userMessageDiv, newContent) {
    const conversation = conversations.find(c => c.id === currentConversationId);
    if (!conversation) return;

    // Trouver l'index du message utilisateur dans la conversation
    const allMessages = document.querySelectorAll('.message');
    const messageIndex = Array.from(allMessages).indexOf(userMessageDiv);

    // Trouver le message dans la conversation
    let userMsgIndex = -1;
    let messagesBeforeThisOne = 0;

    for (let i = 0; i < conversation.messages.length; i++) {
        if (conversation.messages[i].role === 'user') {
            if (messagesBeforeThisOne === Math.floor(messageIndex / 2)) {
                userMsgIndex = i;
                break;
            }
            messagesBeforeThisOne++;
        }
    }

    if (userMsgIndex === -1) return;

    // Supprimer tous les messages après celui-ci (dans la conversation et le DOM)
    const messagesToRemove = conversation.messages.length - userMsgIndex - 1;
    conversation.messages.splice(userMsgIndex + 1, messagesToRemove);

    // Mettre à jour le contenu du message
    conversation.messages[userMsgIndex].content = newContent;
    conversation.updatedAt = new Date().toISOString();
    saveConversationsToStorage();

    // Supprimer les messages suivants du DOM
    let nextElement = userMessageDiv.nextElementSibling;
    while (nextElement) {
        const toRemove = nextElement;
        nextElement = nextElement.nextElementSibling;
        if (toRemove.classList.contains('message')) {
            toRemove.remove();
        }
    }

    // Mettre à jour l'affichage du message
    const messageTextDiv = userMessageDiv.querySelector('.message-text');
    const editContainer = userMessageDiv.querySelector('.message-edit-container');
    const actionsDiv = userMessageDiv.querySelector('.message-actions');

    messageTextDiv.innerHTML = marked.parse(newContent);
    editContainer.remove();
    messageTextDiv.style.display = '';
    actionsDiv.style.display = '';

    // Mettre à jour le data-content du bouton copier
    const copyBtn = userMessageDiv.querySelector('.btn-copy');
    copyBtn.setAttribute('data-content', escapeHtml(newContent));

    // Envoyer le nouveau message
    const typingId = showTypingIndicator();

    try {
        isStreaming = true;
        document.getElementById('sendBtn').style.display = 'none';
        document.getElementById('stopBtn').style.display = 'flex';

        abortController = new AbortController();

        await streamMessage(newContent, typingId);

    } catch (error) {
        console.error('Error resending edited message:', error);
        removeTypingIndicator(typingId);

        if (error.name !== 'AbortError') {
            appendMessage('assistant', '❌ Erreur lors de l\'envoi du message. Veuillez réessayer.', new Date().toISOString());
        }
    } finally {
        isStreaming = false;
        document.getElementById('sendBtn').style.display = 'flex';
        document.getElementById('stopBtn').style.display = 'none';
        abortController = null;
    }
}

async function regenerateResponse(assistantMessageDiv) {
    if (isStreaming) {
        return; // Ne pas régénérer pendant un streaming en cours
    }

    const conversation = conversations.find(c => c.id === currentConversationId);
    if (!conversation || conversation.messages.length < 2) {
        return; // Pas assez de messages
    }

    // Trouver l'index du message assistant dans la conversation
    const messages = conversation.messages;
    let assistantIndex = -1;

    // Parcourir les messages pour trouver celui qui correspond
    for (let i = messages.length - 1; i >= 0; i--) {
        if (messages[i].role === 'assistant') {
            assistantIndex = i;
            break;
        }
    }

    if (assistantIndex === -1 || assistantIndex === 0) {
        return; // Pas de message assistant ou pas de question avant
    }

    // Récupérer le message utilisateur précédent
    const userMessage = messages[assistantIndex - 1];
    if (!userMessage || userMessage.role !== 'user') {
        return;
    }

    // Supprimer visuellement l'ancienne réponse
    assistantMessageDiv.remove();

    // Supprimer le message assistant de la conversation
    conversation.messages.splice(assistantIndex, 1);
    saveConversationsToStorage();

    // Afficher l'indicateur de frappe
    const typingId = showTypingIndicator();

    try {
        isStreaming = true;
        document.getElementById('sendBtn').style.display = 'none';
        document.getElementById('stopBtn').style.display = 'flex';

        abortController = new AbortController();

        // Régénérer la réponse avec streaming
        await streamMessage(userMessage.content, typingId);

    } catch (error) {
        console.error('Error regenerating response:', error);
        removeTypingIndicator(typingId);

        if (error.name !== 'AbortError') {
            appendMessage('assistant', '❌ Erreur lors de la régénération. Veuillez réessayer.', new Date().toISOString());
        }
    } finally {
        isStreaming = false;
        document.getElementById('sendBtn').style.display = 'flex';
        document.getElementById('stopBtn').style.display = 'none';
        abortController = null;
    }
}

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

function removeTypingIndicator(id) {
    const element = document.getElementById(id);
    if (element) {
        element.remove();
    }
}

// Paramètres
function loadSettings() {
    document.getElementById('apiUrl').value = CONFIG.apiUrl;
    document.getElementById('apiKey').value = CONFIG.apiKey;
    document.getElementById('topK').value = CONFIG.topK;
    document.getElementById('showSources').checked = CONFIG.showSources;
}

function saveSettings() {
    CONFIG.apiUrl = document.getElementById('apiUrl').value;
    CONFIG.apiKey = document.getElementById('apiKey').value;
    CONFIG.topK = parseInt(document.getElementById('topK').value);
    CONFIG.showSources = document.getElementById('showSources').checked;

    localStorage.setItem('apiUrl', CONFIG.apiUrl);
    localStorage.setItem('apiKey', CONFIG.apiKey);
    localStorage.setItem('topK', CONFIG.topK);
    localStorage.setItem('showSources', CONFIG.showSources);

    // Fermer le panneau
    document.getElementById('closeSettings').click();

    // Afficher une confirmation
    alert('Paramètres enregistrés avec succès !');
}

// Utilitaires
function scrollToBottom() {
    const container = document.getElementById('messagesContainer');
    container.scrollTop = container.scrollHeight;
}

function formatTime(timestamp) {
    const date = new Date(timestamp);
    return date.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' });
}

function formatDate(timestamp) {
    const date = new Date(timestamp);
    const now = new Date();
    const diffDays = Math.floor((now - date) / (1000 * 60 * 60 * 24));

    if (diffDays === 0) return 'Aujourd\'hui';
    if (diffDays === 1) return 'Hier';
    if (diffDays < 7) return `Il y a ${diffDays} jours`;

    return date.toLocaleDateString('fr-FR', { day: 'numeric', month: 'short' });
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// ============================================================================
// UPLOAD DE FICHIERS
// ============================================================================

let selectedFiles = [];

// Ouvrir la modal d'upload
document.getElementById('uploadBtn').addEventListener('click', () => {
    document.getElementById('uploadModal').style.display = 'flex';
    selectedFiles = [];
    updateFilesList();
});

// Fermer la modal
document.getElementById('closeUploadModal').addEventListener('click', closeUploadModal);
document.getElementById('cancelUpload').addEventListener('click', closeUploadModal);

function closeUploadModal() {
    document.getElementById('uploadModal').style.display = 'none';
    selectedFiles = [];
    updateFilesList();
    document.getElementById('uploadProgress').style.display = 'none';
    document.getElementById('progressFill').style.width = '0%';
}

// Zone de upload - click pour sélectionner
document.getElementById('uploadZone').addEventListener('click', () => {
    document.getElementById('fileInput').click();
});

// Sélection de fichiers
document.getElementById('fileInput').addEventListener('change', (e) => {
    const files = Array.from(e.target.files);
    addFilesToList(files);
});

// Drag and drop
const uploadZone = document.getElementById('uploadZone');

uploadZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    uploadZone.classList.add('dragover');
});

uploadZone.addEventListener('dragleave', () => {
    uploadZone.classList.remove('dragover');
});

uploadZone.addEventListener('drop', (e) => {
    e.preventDefault();
    uploadZone.classList.remove('dragover');
    const files = Array.from(e.dataTransfer.files);
    addFilesToList(files);
});

function addFilesToList(files) {
    // Filtrer les fichiers selon les extensions autorisées (v2 - plus de formats)
    const allowedExtensions = [
        '.pdf', '.txt', '.md', '.html', '.htm', '.jsonl', '.json', '.csv',
        '.docx', '.doc', '.xlsx', '.xls', '.pptx', '.ppt',
        '.png', '.jpg', '.jpeg'
    ];
    const validFiles = files.filter(file => {
        const ext = '.' + file.name.split('.').pop().toLowerCase();
        return allowedExtensions.includes(ext);
    });

    selectedFiles = [...selectedFiles, ...validFiles];
    updateFilesList();
}

function updateFilesList() {
    const listContainer = document.getElementById('uploadFilesList');
    const startUploadBtn = document.getElementById('startUpload');

    if (selectedFiles.length === 0) {
        listContainer.innerHTML = '';
        startUploadBtn.disabled = true;
        return;
    }

    startUploadBtn.disabled = false;

    listContainer.innerHTML = selectedFiles.map((file, index) => {
        const ext = file.name.split('.').pop().toUpperCase();
        const size = formatFileSize(file.size);

        return `
            <div class="upload-file-item">
                <div class="upload-file-item-info">
                    <div class="upload-file-item-icon">${ext}</div>
                    <div class="upload-file-item-details">
                        <div class="upload-file-item-name">${escapeHtml(file.name)}</div>
                        <div class="upload-file-item-size">${size}</div>
                    </div>
                </div>
                <button class="upload-file-item-remove" data-index="${index}">×</button>
            </div>
        `;
    }).join('');

    // Ajouter les event listeners pour supprimer
    listContainer.querySelectorAll('.upload-file-item-remove').forEach(btn => {
        btn.addEventListener('click', () => {
            const index = parseInt(btn.dataset.index);
            selectedFiles.splice(index, 1);
            updateFilesList();
        });
    });
}

function formatFileSize(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

// Démarrer l'upload
document.getElementById('startUpload').addEventListener('click', async () => {
    if (selectedFiles.length === 0) return;

    const progressDiv = document.getElementById('uploadProgress');
    const progressFill = document.getElementById('progressFill');
    const progressText = document.getElementById('progressText');
    const listContainer = document.getElementById('uploadFilesList');

    progressDiv.style.display = 'block';
    document.getElementById('startUpload').disabled = true;
    document.getElementById('cancelUpload').disabled = true;

    let successCount = 0;
    let errorCount = 0;
    const totalFiles = selectedFiles.length;

    for (let i = 0; i < selectedFiles.length; i++) {
        const file = selectedFiles[i];
        const progress = ((i) / totalFiles) * 100;

        progressFill.style.width = progress + '%';
        progressText.textContent = `Indexation en cours : ${file.name}... (${i + 1}/${totalFiles})`;

        try {
            const result = await uploadFile(file, progressText);
            successCount++;

            // Afficher le nombre de chunks indexés
            const chunksInfo = result.chunks_indexed ? ` (${result.chunks_indexed} chunk${result.chunks_indexed > 1 ? 's' : ''})` : '';
            progressText.textContent = `✅ ${file.name} indexé${chunksInfo} - ${i + 1}/${totalFiles}`;

        } catch (error) {
            console.error(`Error uploading ${file.name}:`, error);
            errorCount++;
            progressText.textContent = `❌ Erreur : ${file.name} - ${i + 1}/${totalFiles}`;
        }

        // Petite pause pour que l'utilisateur puisse voir le statut
        await new Promise(resolve => setTimeout(resolve, 500));
    }

    progressFill.style.width = '100%';

    // Afficher le résultat
    if (errorCount === 0) {
        listContainer.innerHTML = `
            <div class="upload-success">
                ✅ ${successCount} fichier(s) uploadé(s) et indexé(s) avec succès !
            </div>
        `;
    } else {
        listContainer.innerHTML = `
            <div class="upload-${successCount > 0 ? 'success' : 'error'}">
                ${successCount > 0 ? `✅ ${successCount} fichier(s) uploadé(s) avec succès<br>` : ''}
                ${errorCount > 0 ? `❌ ${errorCount} fichier(s) en erreur` : ''}
            </div>
        `;
    }

    // Réinitialiser après 3 secondes
    setTimeout(() => {
        closeUploadModal();
    }, 3000);
});

async function uploadFile(file, progressText) {
    const formData = new FormData();
    formData.append('file', file);

    progressText.textContent = `⚙️  Indexation de ${file.name} en cours...`;

    try {
        // Use advanced v2 endpoint with better parsing and chunking
        const response = await fetch(`${CONFIG.apiUrl}/upload/v2`, {
            method: 'POST',
            headers: {
                'X-API-Key': CONFIG.apiKey
            },
            body: formData
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Upload failed');
        }

        const result = await response.json();
        progressText.textContent = `✅ ${result.message}`;

        return result;
    } catch (error) {
        progressText.textContent = `❌ Erreur: ${error.message}`;
        throw error;
    }
}
