/**
 * Documents Module
 * Gestion de la bibliotheque de documents utilisateur
 */

// State local du module
let documentsState = {
    documents: [],
    currentPage: 1,
    totalPages: 1,
    pageSize: 20,
    filter: null,
    searchQuery: '',
    stats: null,
    selectedDocument: null,
    isLoading: false
};

/**
 * Formate une taille en bytes en format lisible
 */
function formatFileSize(bytes) {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

/**
 * Formate une date relative
 */
function formatRelativeDate(dateString) {
    const date = new Date(dateString);
    const now = new Date();
    const diff = now - date;
    const days = Math.floor(diff / (1000 * 60 * 60 * 24));

    if (days === 0) return "Aujourd'hui";
    if (days === 1) return 'Hier';
    if (days < 7) return 'Il y a ' + days + ' jours';
    if (days < 30) return 'Il y a ' + Math.floor(days / 7) + ' semaines';
    return date.toLocaleDateString('fr-FR');
}

/**
 * Retourne l'icone selon le type de fichier
 */
function getFileIcon(fileType) {
    if (fileType.includes('pdf')) return '📄';
    if (fileType.includes('text')) return '📝';
    if (fileType.includes('csv') || fileType.includes('excel') || fileType.includes('spreadsheet')) return '📊';
    if (fileType.includes('json')) return '🔧';
    if (fileType.includes('image')) return '🖼️';
    return '📁';
}

/**
 * Ouvre le modal de gestion des documents
 */
async function openDocumentsModal() {
    const modal = document.getElementById('documentsModal');
    if (!modal) {
        console.error('Modal documents non trouve');
        return;
    }

    modal.style.display = 'flex';
    documentsState.currentPage = 1;
    documentsState.filter = null;
    documentsState.searchQuery = '';

    // Reset les champs de recherche/filtre
    const searchInput = document.getElementById('documentsSearch');
    const filterSelect = document.getElementById('documentsFilter');
    if (searchInput) searchInput.value = '';
    if (filterSelect) filterSelect.value = '';

    await loadDocuments();
    await loadStorageStats();
}

/**
 * Ferme le modal documents
 */
function closeDocumentsModal() {
    const modal = document.getElementById('documentsModal');
    if (modal) {
        modal.style.display = 'none';
    }
    documentsState.selectedDocument = null;
}

/**
 * Charge les documents depuis l'API
 */
async function loadDocuments() {
    if (documentsState.isLoading) return;
    documentsState.isLoading = true;

    const container = document.getElementById('documentsList');
    if (container) {
        container.innerHTML = '<div class="documents-loading">Chargement...</div>';
    }

    try {
        const options = {
            page: documentsState.currentPage,
            page_size: documentsState.pageSize
        };
        if (documentsState.filter) {
            options.visibility = documentsState.filter;
        }

        const response = await ApiService.listUserDocuments(options);
        documentsState.documents = response.documents || [];
        documentsState.totalPages = response.total_pages || 1;

        renderDocuments();
        renderPagination();

    } catch (error) {
        console.error('Erreur chargement documents:', error);
        if (container) {
            container.innerHTML = '<div class="documents-error">Erreur lors du chargement</div>';
        }
        showToast('Erreur lors du chargement des documents', 'error');
    } finally {
        documentsState.isLoading = false;
    }
}

/**
 * Charge les statistiques de stockage
 */
async function loadStorageStats() {
    try {
        const stats = await ApiService.getUserStorageStats();
        documentsState.stats = stats;
        renderStorageStats();
    } catch (error) {
        console.error('Erreur chargement stats:', error);
    }
}

/**
 * Affiche les statistiques de stockage
 */
function renderStorageStats() {
    if (!documentsState.stats) return;

    const stats = documentsState.stats;
    const usedPercent = stats.quota_used_percent || 0;

    // Update storage bar elements
    const usedEl = document.getElementById('storageUsed');
    const quotaEl = document.getElementById('storageQuota');
    const fillEl = document.getElementById('storageFill');

    if (usedEl) usedEl.textContent = formatFileSize(stats.used_bytes);
    if (quotaEl) quotaEl.textContent = stats.quota_bytes ? formatFileSize(stats.quota_bytes) : 'Illimite';
    if (fillEl) {
        fillEl.style.width = usedPercent + '%';
        // Change color based on usage
        fillEl.classList.remove('warning', 'danger');
        if (usedPercent > 90) {
            fillEl.classList.add('danger');
        } else if (usedPercent > 70) {
            fillEl.classList.add('warning');
        }
    }
}

/**
 * Affiche la liste des documents
 */
function renderDocuments() {
    const container = document.getElementById('documentsList');
    if (!container) return;

    if (documentsState.documents.length === 0) {
        container.innerHTML =
            '<div class="documents-empty">' +
                '<span class="empty-icon">📂</span>' +
                '<p>Aucun document</p>' +
                '<p class="empty-hint">Uploadez vos documents pour les utiliser dans le RAG</p>' +
            '</div>';
        return;
    }

    container.innerHTML = documentsState.documents.map(function(doc) {
        return createDocumentItem(doc);
    }).join('');
    attachDocumentEvents();
}

/**
 * Cree le HTML d'un document
 */
function createDocumentItem(doc) {
    const icon = getFileIcon(doc.file_type);
    const visibilityIcon = doc.visibility === 'public' ? '🌍' : '🔒';
    const visibilityClass = doc.visibility === 'public' ? 'public' : 'private';

    return '<div class="document-item" data-id="' + doc.id + '">' +
        '<div class="document-icon">' + icon + '</div>' +
        '<div class="document-info">' +
            '<div class="document-name" title="' + escapeHtml(doc.filename) + '">' +
                escapeHtml(doc.filename) +
            '</div>' +
            '<div class="document-meta">' +
                '<span class="document-size">' + formatFileSize(doc.file_size) + '</span>' +
                '<span class="document-date">' + formatRelativeDate(doc.created_at) + '</span>' +
                '<span class="document-visibility ' + visibilityClass + '" title="' + doc.visibility + '">' +
                    visibilityIcon +
                '</span>' +
                (doc.current_version > 1 ? '<span class="document-version">v' + doc.current_version + '</span>' : '') +
            '</div>' +
        '</div>' +
        '<div class="document-actions">' +
            '<button class="btn-icon btn-download" data-id="' + doc.id + '" title="Telecharger">⬇️</button>' +
            '<button class="btn-icon btn-visibility" data-id="' + doc.id + '" data-visibility="' + doc.visibility + '" title="Changer visibilite">' + visibilityIcon + '</button>' +
            '<button class="btn-icon btn-replace" data-id="' + doc.id + '" title="Remplacer">🔄</button>' +
            '<button class="btn-icon btn-delete" data-id="' + doc.id + '" title="Supprimer">🗑️</button>' +
        '</div>' +
    '</div>';
}

/**
 * Attache les event listeners aux documents
 */
function attachDocumentEvents() {
    // Download
    document.querySelectorAll('.document-item .btn-download').forEach(function(btn) {
        btn.addEventListener('click', function(e) {
            e.stopPropagation();
            downloadDocument(btn.dataset.id);
        });
    });

    // Toggle visibility
    document.querySelectorAll('.document-item .btn-visibility').forEach(function(btn) {
        btn.addEventListener('click', function(e) {
            e.stopPropagation();
            toggleVisibility(btn.dataset.id, btn.dataset.visibility);
        });
    });

    // Replace
    document.querySelectorAll('.document-item .btn-replace').forEach(function(btn) {
        btn.addEventListener('click', function(e) {
            e.stopPropagation();
            showReplaceDialog(btn.dataset.id);
        });
    });

    // Delete
    document.querySelectorAll('.document-item .btn-delete').forEach(function(btn) {
        btn.addEventListener('click', function(e) {
            e.stopPropagation();
            deleteDocument(btn.dataset.id);
        });
    });

    // Click sur document pour details
    document.querySelectorAll('.document-item').forEach(function(item) {
        item.addEventListener('click', function() {
            showDocumentDetails(item.dataset.id);
        });
    });
}

/**
 * Affiche la pagination
 */
function renderPagination() {
    const container = document.getElementById('documentsPagination');
    const infoEl = document.getElementById('docsPaginationInfo');
    const prevBtn = document.getElementById('docsPrevPage');
    const nextBtn = document.getElementById('docsNextPage');

    if (!container) return;

    if (documentsState.totalPages <= 1) {
        container.style.display = 'none';
        return;
    }

    container.style.display = 'flex';

    // Update info text
    if (infoEl) {
        infoEl.textContent = 'Page ' + documentsState.currentPage + '/' + documentsState.totalPages;
    }

    // Update button states
    if (prevBtn) {
        prevBtn.disabled = documentsState.currentPage <= 1;
    }
    if (nextBtn) {
        nextBtn.disabled = documentsState.currentPage >= documentsState.totalPages;
    }
}

/**
 * Recherche dans les documents
 */
async function searchDocuments() {
    const input = document.getElementById('documentsSearch');
    const query = input ? input.value.trim() : '';

    if (query.length < 2) {
        documentsState.searchQuery = '';
        await loadDocuments();
        return;
    }

    documentsState.searchQuery = query;
    documentsState.isLoading = true;

    const container = document.getElementById('documentsList');
    if (container) {
        container.innerHTML = '<div class="documents-loading">Recherche...</div>';
    }

    try {
        const response = await ApiService.searchUserDocuments(query, documentsState.filter);
        documentsState.documents = response.results || [];
        documentsState.totalPages = 1;

        renderDocuments();
        renderPagination();

    } catch (error) {
        console.error('Erreur recherche:', error);
        showToast('Erreur lors de la recherche', 'error');
    } finally {
        documentsState.isLoading = false;
    }
}

/**
 * Filtre par visibilite
 */
async function filterByVisibility(visibility) {
    documentsState.filter = visibility || null;
    documentsState.currentPage = 1;

    if (documentsState.searchQuery) {
        await searchDocuments();
    } else {
        await loadDocuments();
    }
}

/**
 * Telecharge un document
 */
async function downloadDocument(docId) {
    try {
        const doc = documentsState.documents.find(function(d) { return d.id === docId; });
        const filename = doc ? doc.filename : 'document';

        const blob = await ApiService.downloadUserDocument(docId);
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);

        showToast('Telechargement lance', 'success');
    } catch (error) {
        console.error('Erreur telechargement:', error);
        showToast('Erreur lors du telechargement', 'error');
    }
}

/**
 * Change la visibilite d'un document
 */
async function toggleVisibility(docId, currentVisibility) {
    const newVisibility = currentVisibility === 'public' ? 'private' : 'public';

    try {
        await ApiService.updateUserDocument(docId, { visibility: newVisibility });
        showToast('Document ' + (newVisibility === 'public' ? 'public' : 'prive'), 'success');
        await loadDocuments();
    } catch (error) {
        console.error('Erreur changement visibilite:', error);
        showToast('Erreur lors du changement', 'error');
    }
}

/**
 * Supprime un document
 */
async function deleteDocument(docId) {
    const doc = documentsState.documents.find(function(d) { return d.id === docId; });
    const filename = doc ? doc.filename : 'ce document';

    const confirmed = await showConfirm({
        title: 'Supprimer le document',
        message: 'Etes-vous sur de vouloir supprimer "' + escapeHtml(filename) + '" ? Cette action est irreversible.',
        confirmText: 'Supprimer',
        cancelText: 'Annuler',
        type: 'danger'
    });

    if (!confirmed) return;

    try {
        await ApiService.deleteUserDocument(docId);
        showToast('Document supprime', 'success');
        await loadDocuments();
        await loadStorageStats();
    } catch (error) {
        console.error('Erreur suppression:', error);
        showToast('Erreur lors de la suppression', 'error');
    }
}

/**
 * Affiche le dialog de remplacement
 */
function showReplaceDialog(docId) {
    documentsState.selectedDocument = docId;

    var input = document.createElement('input');
    input.type = 'file';
    input.accept = '.pdf,.txt,.csv,.json';

    input.onchange = async function(e) {
        const file = e.target.files[0];
        if (!file) return;

        try {
            await ApiService.replaceUserDocument(docId, file, 'Nouvelle version');
            showToast('Document remplace avec succes', 'success');
            await loadDocuments();
            await loadStorageStats();
        } catch (error) {
            console.error('Erreur remplacement:', error);
            showToast(error.message || 'Erreur lors du remplacement', 'error');
        }
    };

    input.click();
}

/**
 * Affiche les details d'un document
 */
async function showDocumentDetails(docId) {
    try {
        const doc = await ApiService.getUserDocument(docId);

        var detailsHtml =
            '<div class="document-details-modal">' +
                '<div class="details-header">' +
                    '<h3>' + getFileIcon(doc.file_type) + ' ' + escapeHtml(doc.filename) + '</h3>' +
                    '<button class="btn-close" onclick="closeDocumentDetails()">×</button>' +
                '</div>' +
                '<div class="details-content">' +
                    '<div class="detail-row"><span class="detail-label">Taille</span><span class="detail-value">' + formatFileSize(doc.file_size) + '</span></div>' +
                    '<div class="detail-row"><span class="detail-label">Type</span><span class="detail-value">' + doc.file_type + '</span></div>' +
                    '<div class="detail-row"><span class="detail-label">Visibilite</span><span class="detail-value">' + (doc.visibility === 'public' ? '🌍 Public' : '🔒 Prive') + '</span></div>' +
                    '<div class="detail-row"><span class="detail-label">Version</span><span class="detail-value">v' + doc.current_version + '</span></div>' +
                    '<div class="detail-row"><span class="detail-label">Indexe RAG</span><span class="detail-value">' + (doc.is_indexed ? '✅ Oui' : '❌ Non') + '</span></div>' +
                    '<div class="detail-row"><span class="detail-label">Chunks</span><span class="detail-value">' + doc.chunk_count + '</span></div>' +
                    '<div class="detail-row"><span class="detail-label">Cree le</span><span class="detail-value">' + new Date(doc.created_at).toLocaleString('fr-FR') + '</span></div>' +
                    renderVersionsSection(doc.versions) +
                '</div>' +
            '</div>';

        var overlay = document.getElementById('documentDetailsOverlay');
        if (!overlay) {
            overlay = document.createElement('div');
            overlay.id = 'documentDetailsOverlay';
            overlay.className = 'document-details-overlay';
            document.body.appendChild(overlay);
        }

        overlay.innerHTML = detailsHtml;
        overlay.style.display = 'flex';

        overlay.addEventListener('click', function(e) {
            if (e.target === overlay) {
                closeDocumentDetails();
            }
        });

    } catch (error) {
        console.error('Erreur chargement details:', error);
        showToast('Erreur lors du chargement des details', 'error');
    }
}

/**
 * Rend la section des versions
 */
function renderVersionsSection(versions) {
    if (!versions || versions.length === 0) return '';

    var html = '<div class="versions-section"><h4>Historique des versions</h4><div class="versions-list">';
    versions.forEach(function(v) {
        html += '<div class="version-item">' +
            '<span class="version-number">v' + v.version_number + '</span>' +
            '<span class="version-date">' + new Date(v.created_at).toLocaleString('fr-FR') + '</span>' +
            '<span class="version-size">' + formatFileSize(v.file_size) + '</span>' +
            (v.comment ? '<span class="version-comment">' + escapeHtml(v.comment) + '</span>' : '') +
        '</div>';
    });
    html += '</div></div>';
    return html;
}

/**
 * Ferme les details du document
 */
function closeDocumentDetails() {
    const overlay = document.getElementById('documentDetailsOverlay');
    if (overlay) {
        overlay.style.display = 'none';
    }
}

/**
 * Upload d'un nouveau document depuis le modal
 */
async function uploadNewDocument() {
    var input = document.createElement('input');
    input.type = 'file';
    input.accept = '.pdf,.txt,.csv,.json';
    input.multiple = true;

    input.onchange = async function(e) {
        const files = Array.from(e.target.files);
        if (files.length === 0) return;

        const visibilitySelect = document.getElementById('uploadVisibility');
        const visibility = visibilitySelect ? visibilitySelect.value : 'public';
        var successCount = 0;
        var errorCount = 0;

        for (var i = 0; i < files.length; i++) {
            try {
                await ApiService.uploadUserDocument(files[i], visibility);
                successCount++;
            } catch (error) {
                console.error('Erreur upload ' + files[i].name + ':', error);
                errorCount++;
            }
        }

        if (successCount > 0) {
            showToast(successCount + ' document(s) uploade(s)', 'success');
            await loadDocuments();
            await loadStorageStats();
        }
        if (errorCount > 0) {
            showToast(errorCount + ' erreur(s) d\'upload', 'error');
        }
    };

    input.click();
}

/**
 * Initialise les event listeners du module
 */
function initDocumentsEvents() {
    // Bouton ouvrir modal (dans sidebar)
    var openBtn = document.getElementById('documentsBtn');
    if (openBtn) {
        openBtn.addEventListener('click', openDocumentsModal);
    }

    // Bouton fermer modal
    var closeBtn = document.getElementById('closeDocumentsModal');
    if (closeBtn) {
        closeBtn.addEventListener('click', closeDocumentsModal);
    }

    // Click hors modal pour fermer
    var modal = document.getElementById('documentsModal');
    if (modal) {
        modal.addEventListener('click', function(e) {
            if (e.target === modal) {
                closeDocumentsModal();
            }
        });
    }

    // Recherche avec debounce
    var searchInput = document.getElementById('documentsSearch');
    if (searchInput) {
        var debounceTimer;
        searchInput.addEventListener('input', function() {
            clearTimeout(debounceTimer);
            debounceTimer = setTimeout(searchDocuments, 300);
        });
    }

    // Filtre visibilite
    var filterSelect = document.getElementById('documentsVisibilityFilter');
    if (filterSelect) {
        filterSelect.addEventListener('change', function() {
            filterByVisibility(filterSelect.value);
        });
    }

    // Bouton upload dans le modal documents
    var uploadBtn = document.getElementById('documentsUploadBtn');
    if (uploadBtn) {
        uploadBtn.addEventListener('click', uploadNewDocument);
    }

    // Fermer details modal
    var closeDetailsBtn = document.getElementById('closeDocumentDetails');
    if (closeDetailsBtn) {
        closeDetailsBtn.addEventListener('click', function() {
            document.getElementById('documentDetailsModal').style.display = 'none';
        });
    }

    // Pagination
    var prevBtn = document.getElementById('docsPrevPage');
    var nextBtn = document.getElementById('docsNextPage');
    if (prevBtn) {
        prevBtn.addEventListener('click', function() {
            if (documentsState.currentPage > 1) {
                documentsState.currentPage--;
                loadDocuments();
            }
        });
    }
    if (nextBtn) {
        nextBtn.addEventListener('click', function() {
            if (documentsState.currentPage < documentsState.totalPages) {
                documentsState.currentPage++;
                loadDocuments();
            }
        });
    }
}

// Export pour utilisation globale
window.DocumentsModule = {
    open: openDocumentsModal,
    close: closeDocumentsModal,
    load: loadDocuments,
    init: initDocumentsEvents
};

window.openDocumentsModal = openDocumentsModal;
window.closeDocumentsModal = closeDocumentsModal;
window.closeDocumentDetails = closeDocumentDetails;
