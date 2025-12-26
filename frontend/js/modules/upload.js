/**
 * Upload Module
 *
 * Gestion de l'upload et indexation de fichiers
 */

let selectedFiles = [];

/**
 * Ouvre la modale d'upload
 */
function openUploadModal() {
    document.getElementById('uploadModal').style.display = 'flex';
    selectedFiles = [];
    updateFilesList();
}

/**
 * Ferme la modale d'upload
 */
function closeUploadModal() {
    document.getElementById('uploadModal').style.display = 'none';
    selectedFiles = [];
    updateFilesList();
    document.getElementById('uploadProgress').style.display = 'none';
    document.getElementById('progressFill').style.width = '0%';
}

/**
 * Initialise les event listeners d'upload
 */
function initializeUpload() {
    // Bouton upload header
    document.getElementById('uploadBtn').addEventListener('click', openUploadModal);

    // Bouton upload sidebar
    const uploadBtnSidebar = document.getElementById('uploadBtnSidebar');
    if (uploadBtnSidebar) {
        uploadBtnSidebar.addEventListener('click', openUploadModal);
    }

    // Fermeture modale
    document.getElementById('closeUploadModal').addEventListener('click', closeUploadModal);
    document.getElementById('cancelUpload').addEventListener('click', closeUploadModal);

    // Zone de drop
    document.getElementById('uploadZone').addEventListener('click', () => {
        document.getElementById('fileInput').click();
    });

    document.getElementById('fileInput').addEventListener('change', (e) => {
        addFilesToList(Array.from(e.target.files));
    });

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
        addFilesToList(Array.from(e.dataTransfer.files));
    });

    // Demarrer l'upload
    document.getElementById('startUpload').addEventListener('click', startUpload);
}

/**
 * Ajoute des fichiers a la liste
 * @param {File[]} files - Fichiers a ajouter
 */
function addFilesToList(files) {
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

/**
 * Met a jour l'affichage de la liste de fichiers
 */
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
                <button class="upload-file-item-remove" data-index="${index}">x</button>
            </div>
        `;
    }).join('');

    listContainer.querySelectorAll('.upload-file-item-remove').forEach(btn => {
        btn.addEventListener('click', () => {
            selectedFiles.splice(parseInt(btn.dataset.index), 1);
            updateFilesList();
        });
    });
}

/**
 * Demarre l'upload des fichiers
 */
async function startUpload() {
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
        progressText.textContent = `Indexation: ${file.name}... (${i + 1}/${totalFiles})`;

        try {
            const result = await ApiService.uploadFile(file);
            successCount++;
            const chunksInfo = result.chunks_indexed ? ` (${result.chunks_indexed} chunks)` : '';
            progressText.textContent = `${file.name} indexe${chunksInfo}`;
        } catch (error) {
            console.error(`Error uploading ${file.name}:`, error);
            errorCount++;
            progressText.textContent = `Erreur: ${file.name}`;
        }

        await new Promise(resolve => setTimeout(resolve, 500));
    }

    progressFill.style.width = '100%';

    if (errorCount === 0) {
        listContainer.innerHTML = `<div class="upload-success">${successCount} fichier(s) indexe(s) !</div>`;
    } else {
        listContainer.innerHTML = `
            <div class="upload-${successCount > 0 ? 'success' : 'error'}">
                ${successCount > 0 ? `${successCount} fichier(s) indexe(s)<br>` : ''}
                ${errorCount > 0 ? `${errorCount} fichier(s) en erreur` : ''}
            </div>
        `;
    }

    setTimeout(closeUploadModal, 3000);
}

// Export global
window.UploadModule = {
    initialize: initializeUpload,
    open: openUploadModal,
    close: closeUploadModal,
    start: startUpload
};

// Exports individuels
window.initializeUpload = initializeUpload;
window.openUploadModal = openUploadModal;
window.closeUploadModal = closeUploadModal;
