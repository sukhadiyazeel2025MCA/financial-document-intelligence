document.addEventListener('DOMContentLoaded', () => {
    loadDocuments();
    setupDropZone();
    setupForm();

    document.getElementById('refresh-btn').addEventListener('click', loadDocuments);
    
    const clearBtn = document.getElementById('clear-all-btn');
    if (clearBtn) {
        clearBtn.addEventListener('click', async () => {
            if (confirm('Are you sure you want to delete all processed documents? This action cannot be undone.')) {
                try {
                    const res = await fetch('/api/v1/documents', { method: 'DELETE' });
                    if (res.ok) {
                        showToast('All documents cleared successfully', 'success');
                        loadDocuments();
                    } else {
                        showToast('Failed to clear documents', 'error');
                    }
                } catch (err) {
                    showToast('Error clearing documents', 'error');
                }
            }
        });
    }
});

async function loadDocuments() {
    const tableBody = document.getElementById('documents-body');
    const loading = document.getElementById('table-loading');
    const emptyState = document.getElementById('empty-state');
    const table = document.getElementById('documents-table');

    loading.style.display = 'block';
    table.style.display = 'none';
    emptyState.style.display = 'none';

    try {
        const response = await fetch('/api/v1/documents');
        if (!response.ok) throw new Error('Failed to fetch documents');
        
        const resJson = await response.json();
        const docsList = Array.isArray(resJson) ? resJson : (resJson.documents || []);
        
        loading.style.display = 'none';
        
        if (docsList.length > 0) {
            tableBody.innerHTML = '';
            docsList.forEach((doc, index) => {
                const tr = document.createElement('tr');
                
                const status = doc.processing_status || doc.status || 'UNKNOWN';
                const statusClass = status === 'PASS' ? 'badge-pass' : (status === 'FAILED' ? 'badge-fail' : 'badge-gray');
                const conf = doc.overall_confidence !== undefined ? doc.overall_confidence : doc.confidence;
                const confDisplay = (conf !== null && conf !== undefined) ? `${(conf * 100).toFixed(1)}%` : 'N/A';
                const docDate = doc.created_at || doc.processed_at;
                
                tr.innerHTML = `
                    <td>${index + 1}</td>
                    <td style="font-weight: 500;">${doc.document_name}</td>
                    <td><span class="badge badge-info">${formatDocumentType(doc.document_type)}</span></td>
                    <td><span class="badge ${statusClass}">${status}</span></td>
                    <td>${confDisplay}</td>
                    <td>${formatDate(docDate)}</td>
                    <td style="white-space: nowrap;">
                        <a href="/result/${doc.id}" class="btn btn-sm btn-secondary" style="margin-right: 6px;">View Results</a>
                        <button class="btn btn-sm btn-delete-row" data-id="${doc.id}" style="background: #fee2e2; color: #991b1b; border: 1px solid #fca5a5; cursor: pointer;">Delete</button>
                    </td>
                `;
                tableBody.appendChild(tr);
            });
            
            // Add row delete handlers
            document.querySelectorAll('.btn-delete-row').forEach(btn => {
                btn.addEventListener('click', async (e) => {
                    const id = e.target.getAttribute('data-id');
                    if (confirm(`Delete document record #${id}?`)) {
                        try {
                            const res = await fetch(`/api/v1/documents/${id}`, { method: 'DELETE' });
                            if (res.ok) {
                                showToast('Document deleted', 'success');
                                loadDocuments();
                            } else {
                                showToast('Failed to delete document', 'error');
                            }
                        } catch (err) {
                            showToast('Error deleting document', 'error');
                        }
                    }
                });
            });

            table.style.display = 'table';
        } else {
            emptyState.style.display = 'block';
        }
    } catch (error) {
        console.error('Error loading documents:', error);
        loading.style.display = 'none';
        showToast('Error loading documents', 'error');
    }
}

function setupDropZone() {
    const dropZone = document.getElementById('drop-zone');
    const fileInput = document.getElementById('file-input');
    const fileName = document.getElementById('file-name');

    dropZone.addEventListener('click', () => fileInput.click());

    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.classList.add('dragover');
    });

    dropZone.addEventListener('dragleave', () => {
        dropZone.classList.remove('dragover');
    });

    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.classList.remove('dragover');
        
        if (e.dataTransfer.files.length) {
            fileInput.files = e.dataTransfer.files;
            updateFileName();
        }
    });

    fileInput.addEventListener('change', updateFileName);

    function updateFileName() {
        if (fileInput.files.length > 0) {
            const name = fileInput.files[0].name;
            fileName.textContent = name;
            
            // Auto-select type dropdown based on filename if clearly matching
            const lower = name.toLowerCase();
            const typeSelect = document.getElementById('document-type');
            if (typeSelect) {
                if (lower.includes('balance') || lower.includes('balance_sheet')) {
                    typeSelect.value = 'balance_sheet';
                } else if (lower.includes('cash') || lower.includes('cash_flow')) {
                    typeSelect.value = 'cash_flow_statement';
                } else if (lower.includes('profit') || lower.includes('p&l') || lower.includes('income')) {
                    typeSelect.value = 'profit_and_loss';
                } else if (lower.includes('invoice') || lower.includes('bill') || lower.includes('inv_')) {
                    typeSelect.value = 'invoice';
                }
            }
        } else {
            fileName.textContent = '';
        }
    }
}

function setupForm() {
    const form = document.getElementById('upload-form');
    
    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const fileInput = document.getElementById('file-input');
        const typeSelect = document.getElementById('document-type');
        
        if (!fileInput.files.length) {
            showToast('Please select a file', 'error');
            return;
        }

        const formData = new FormData();
        formData.append('file', fileInput.files[0]);
        formData.append('document_type', typeSelect.value);

        await processDocument(formData);
    });
}

async function processDocument(formData) {
    const overlay = document.getElementById('processing-overlay');
    const btn = document.getElementById('process-btn');
    const form = document.getElementById('upload-form');
    const fileName = document.getElementById('file-name');
    
    overlay.style.display = 'flex';
    btn.disabled = true;

    try {
        const response = await fetch('/api/v1/documents/process', {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        if (response.ok) {
            showToast('Document processed successfully!', 'success');
            form.reset();
            fileName.textContent = '';
            loadDocuments();
        } else {
            showToast(data.detail || 'Error processing document', 'error');
        }
    } catch (error) {
        console.error('Processing error:', error);
        showToast('Network error during processing', 'error');
    } finally {
        overlay.style.display = 'none';
        btn.disabled = false;
    }
}

function showToast(message, type) {
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    
    document.body.appendChild(toast);
    
    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateY(20px)';
        toast.style.transition = 'all 0.3s ease';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

function formatDocumentType(type) {
    const map = {
        'invoice': 'Invoice',
        'balance_sheet': 'Balance Sheet',
        'profit_and_loss': 'Profit & Loss',
        'cash_flow_statement': 'Cash Flow Statement'
    };
    return map[type] || type;
}

function formatDate(isoString) {
    if (!isoString) return 'N/A';
    const d = new Date(isoString);
    return d.toLocaleString();
}
