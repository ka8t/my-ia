/**
 * Markdown Component
 *
 * Configuration et rendu Markdown avec highlight.js
 */

/**
 * Initialise la configuration de marked
 */
function initializeMarkdown() {
    if (typeof marked !== 'undefined') {
        marked.setOptions({
            highlight: function(code, lang) {
                if (typeof hljs !== 'undefined') {
                    if (lang && hljs.getLanguage(lang)) {
                        return hljs.highlight(code, { language: lang }).value;
                    }
                    return hljs.highlightAuto(code).value;
                }
                return code;
            },
            breaks: true,
            gfm: true
        });
    }
}

/**
 * Rend du Markdown en HTML
 * @param {string} content - Contenu Markdown
 * @returns {string} HTML rendu
 */
function renderMarkdown(content) {
    if (typeof marked !== 'undefined' && marked.parse) {
        return marked.parse(content);
    }
    return content;
}

/**
 * Met en surbrillance le code dans un element
 * @param {HTMLElement} element - Element contenant du code
 */
function highlightCode(element) {
    if (typeof hljs !== 'undefined') {
        element.querySelectorAll('pre code').forEach((block) => {
            hljs.highlightElement(block);
        });
    }
}

// Initialisation auto
document.addEventListener('DOMContentLoaded', initializeMarkdown);

// Export global
window.MarkdownComponent = {
    initialize: initializeMarkdown,
    render: renderMarkdown,
    highlightCode
};

window.renderMarkdown = renderMarkdown;
