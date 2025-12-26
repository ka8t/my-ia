/**
 * Streaming Module
 *
 * Gestion de l'envoi de messages et du streaming des reponses
 */

/**
 * Envoie un message
 */
async function sendMessage() {
    const input = document.getElementById('messageInput');
    const message = input.value.trim();

    if (!message || window.isStreaming) return;

    // Masquer le message de bienvenue
    document.querySelector('.welcome-message')?.remove();

    // Ajouter le message utilisateur
    appendMessage('user', message, new Date().toISOString());

    // Mettre a jour le titre si premier message
    const conversation = window.conversations.find(c => c.id === window.currentConversationId);
    if (conversation && conversation.messages.length === 0) {
        await updateConversationTitle(message);
    }

    // Reinitialiser l'input
    input.value = '';
    input.style.height = 'auto';
    document.getElementById('charCount').textContent = '0 caracteres';

    // Indicateur de frappe
    const typingId = showTypingIndicator();

    try {
        window.isStreaming = true;
        document.getElementById('sendBtn').style.display = 'none';
        document.getElementById('stopBtn').style.display = 'flex';

        window.abortController = new AbortController();

        await streamMessage(message, typingId);

    } catch (error) {
        console.error('Error sending message:', error);
        removeTypingIndicator(typingId);

        if (error.name !== 'AbortError') {
            appendMessage('assistant', 'Desole, une erreur est survenue. Verifiez que l\'API est accessible.', new Date().toISOString());
        }
    } finally {
        window.isStreaming = false;
        document.getElementById('sendBtn').style.display = 'flex';
        document.getElementById('stopBtn').style.display = 'none';
        window.abortController = null;
    }
}

/**
 * Stream la reponse du serveur
 * @param {string} message - Message utilisateur
 * @param {string} typingId - ID de l'indicateur de frappe
 */
async function streamMessage(message, typingId) {
    if (window.DEBUG) console.log('[Stream] Starting for:', message);

    const startTime = Date.now();

    // Timer et indicateur d'attente
    const userMessages = document.querySelectorAll('.message.user');
    const lastUserMessage = userMessages[userMessages.length - 1];
    let timerInterval = null;
    let timerElement = null;
    let waitingIndicator = null;
    let firstChunkReceived = false;

    if (lastUserMessage) {
        // Timer
        timerElement = document.createElement('span');
        timerElement.className = 'message-timer';
        timerElement.textContent = '0.0s';
        const headerDiv = lastUserMessage.querySelector('.message-header');
        if (headerDiv) {
            headerDiv.appendChild(timerElement);
        }

        // Animation d'attente
        waitingIndicator = document.createElement('div');
        waitingIndicator.className = 'waiting-indicator';
        waitingIndicator.innerHTML = `
            <div class="waiting-dots">
                <span></span><span></span><span></span>
            </div>
            <span class="waiting-text">En attente de reponse...</span>
        `;
        lastUserMessage.querySelector('.message-content').appendChild(waitingIndicator);

        timerInterval = setInterval(() => {
            const elapsed = ((Date.now() - startTime) / 1000).toFixed(1);
            timerElement.textContent = `${elapsed}s`;
        }, 100);
    }

    const response = await ApiService.streamChat(message, window.currentConversationId, window.abortController.signal);

    if (window.DEBUG) console.log('[Stream] Response:', response.status);

    if (!response.ok) {
        if (timerInterval) clearInterval(timerInterval);
        if (waitingIndicator) waitingIndicator.remove();
        throw new Error(`HTTP error! status: ${response.status}`);
    }

    removeTypingIndicator(typingId);

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let assistantMessageDiv = null;
    let fullResponse = '';
    let buffer = '';
    let chunkCount = 0;

    while (true) {
        const { done, value } = await reader.read();

        if (done) {
            if (window.DEBUG) console.log('[Stream] Done. Chunks:', chunkCount, 'Length:', fullResponse.length);
            break;
        }

        chunkCount++;
        const chunk = decoder.decode(value, { stream: true });
        if (window.DEBUG && chunkCount <= 3) console.log('[Stream] Chunk', chunkCount, ':', chunk.substring(0, 100));
        buffer += chunk;

        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
            if (!line.trim()) continue;

            try {
                const data = JSON.parse(line);

                if (data.response) {
                    // Premier chunk: arreter le timer
                    if (!firstChunkReceived) {
                        firstChunkReceived = true;
                        const ttft = ((Date.now() - startTime) / 1000).toFixed(1);

                        if (timerInterval) {
                            clearInterval(timerInterval);
                            timerInterval = null;
                        }
                        if (timerElement) {
                            timerElement.textContent = `${ttft}s`;
                            timerElement.classList.add('timer-done');
                        }
                        if (waitingIndicator) {
                            waitingIndicator.remove();
                            waitingIndicator = null;
                        }
                    }

                    fullResponse += data.response;

                    if (!assistantMessageDiv) {
                        assistantMessageDiv = createMessageElement('assistant', '', new Date().toISOString());
                        assistantMessageDiv.classList.add('streaming');
                        document.getElementById('messagesContainer').appendChild(assistantMessageDiv);
                    }

                    const contentDiv = assistantMessageDiv.querySelector('.message-text');
                    if (typeof marked !== 'undefined' && marked.parse) {
                        contentDiv.innerHTML = marked.parse(fullResponse);
                    } else {
                        contentDiv.textContent = fullResponse;
                    }
                    scrollToBottom();
                }

                if (data.done) {
                    // Fin du stream
                    if (assistantMessageDiv) {
                        assistantMessageDiv.classList.remove('streaming');
                    }

                    const totalTime = timerElement ? parseFloat(timerElement.textContent) : 0;
                    if (window.DEBUG) console.log('[Stream] Completed in', totalTime, 's');

                    // Sauvegarder en BDD
                    try {
                        await ApiService.addMessage(window.currentConversationId, 'user', message, null, totalTime);
                        await ApiService.addMessage(window.currentConversationId, 'assistant', fullResponse);
                        if (window.DEBUG) console.log('[Stream] Messages saved');
                    } catch (saveError) {
                        console.error('[Stream] Error saving:', saveError);
                    }

                    // Mettre a jour la conversation locale
                    const conversation = window.conversations.find(c => c.id === window.currentConversationId);
                    if (conversation) {
                        conversation.messages.push({
                            sender_type: 'user',
                            content: message,
                            created_at: new Date().toISOString(),
                            response_time: totalTime
                        });
                        conversation.messages.push({
                            sender_type: 'assistant',
                            content: fullResponse,
                            created_at: new Date().toISOString()
                        });
                        conversation.messagesCount = conversation.messages.length;
                    }
                }
            } catch (e) {
                console.error('Error parsing JSON:', e.message);
            }
        }
    }
}

/**
 * Arrete la generation en cours
 */
function stopGeneration() {
    if (window.abortController) {
        window.abortController.abort();
        window.isStreaming = false;
        document.getElementById('sendBtn').style.display = 'flex';
        document.getElementById('stopBtn').style.display = 'none';
    }
}

// Export global
window.StreamingModule = {
    send: sendMessage,
    stream: streamMessage,
    stop: stopGeneration
};

// Exports individuels
window.sendMessage = sendMessage;
window.streamMessage = streamMessage;
window.stopGeneration = stopGeneration;
