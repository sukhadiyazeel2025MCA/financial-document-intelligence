document.addEventListener('DOMContentLoaded', async () => {
    // Extract ID from URL
    const pathParts = window.location.pathname.split('/');
    const docId = pathParts[pathParts.length - 1];
    
    if (!docId) {
        showError("Document ID not found in URL");
        return;
    }

    try {
        let fullData = null;
        
        // Directly fetch by ID first for guaranteed accuracy
        const idRes = await fetch(`/api/v1/documents/id/${docId}`);
        if (idRes.ok) {
            fullData = await idRes.json();
        } else {
            // Fallback: list documents to find name
            const listRes = await fetch('/api/v1/documents');
            if (!listRes.ok) throw new Error("Failed to fetch documents list");
            const listJson = await listRes.json();
            const docsList = Array.isArray(listJson) ? listJson : (listJson.documents || []);
            const docInfo = docsList.find(d => d.id.toString() === docId);
            if (!docInfo) {
                showError("Document not found");
                return;
            }
            const detailRes = await fetch(`/api/v1/documents/${encodeURIComponent(docInfo.document_name)}`);
            if (!detailRes.ok) throw new Error("Failed to fetch document details");
            fullData = await detailRes.json();
        }

        renderPage(fullData);

    } catch (err) {
        console.error(err);
        showError(err.message);
    }
});

function showError(msg) {
    document.getElementById('page-loading').innerHTML = `
        <div style="color: var(--danger); font-weight: 500;">Error: ${msg}</div>
        <a href="/" class="btn btn-secondary" style="margin-top: 16px; display: inline-block;">&larr; Go Back</a>
    `;
}

function renderPage(data) {
    document.getElementById('page-loading').style.display = 'none';
    document.getElementById('content-container').style.display = 'block';

    renderDocumentHeader(data);
    
    if (data.file_validation) renderFileValidation(data.file_validation);
    if (data.extracted_data) renderExtractedData(data.extracted_data);
    if (data.validation) renderValidation(data.validation);
    if (data.processing_metadata) renderMetadata(data.processing_metadata);
    
    renderRawJSON(data);
}

function renderDocumentHeader(data) {
    document.getElementById('doc-name').textContent = data.document_name || 'Unknown Document';
    document.getElementById('doc-type-badge').textContent = formatDocumentType(data.document_type);
    
    const statusBadge = document.getElementById('doc-status-badge');
    const status = data.processing_status || data.status || 'UNKNOWN';
    statusBadge.textContent = status;
    if (status === 'PASS') statusBadge.className = 'badge badge-pass';
    else if (status === 'FAILED') statusBadge.className = 'badge badge-fail';
    else statusBadge.className = 'badge badge-gray';
    
    document.getElementById('doc-timestamp').textContent = formatDate(data.processing_metadata?.processed_at);
    document.getElementById('doc-time').textContent = data.processing_metadata?.processing_time_ms ? `${data.processing_metadata.processing_time_ms} ms` : 'N/A';
    
    const conf = data.overall_confidence !== undefined ? data.overall_confidence : data.processing_metadata?.overall_confidence;
    document.getElementById('doc-confidence').textContent = (conf !== null && conf !== undefined) ? `${(conf * 100).toFixed(1)}%` : 'N/A';
}

function renderFileValidation(fv) {
    const grid = document.getElementById('file-validation-grid');
    grid.innerHTML = '';
    
    const addRow = (key, val, isBool = false) => {
        let valHtml = val;
        if (isBool) {
            valHtml = val ? '<span style="color: var(--success); font-weight: bold;">✓ PASS</span>' : '<span style="color: var(--danger); font-weight: bold;">✗ FAIL</span>';
        }
        grid.innerHTML += `
            <div class="kv-key">${key}</div>
            <div class="kv-value">${valHtml}</div>
        `;
    };

    addRow('File Type', fv.file_type);
    addRow('Supported', fv.is_supported, true);
    addRow('Readable', fv.is_readable, true);
    addRow('Page Count', fv.page_count);
    addRow('Status', fv.status === 'PASS' ? '<span class="badge badge-pass">PASS</span>' : '<span class="badge badge-fail">FAIL</span>');
}

function renderExtractedData(ed) {
    const container = document.getElementById('extracted-data-container');
    container.innerHTML = '';
    
    const fieldsGrid = document.createElement('div');
    fieldsGrid.className = 'kv-grid';
    fieldsGrid.style.marginBottom = '24px';
    
    let hasSimpleFields = false;

    // Helper to render nested object or array
    for (const [key, value] of Object.entries(ed)) {
        if (Array.isArray(value)) {
            // Render as table
            const tableSection = document.createElement('div');
            tableSection.style.marginTop = '24px';
            tableSection.innerHTML = `<h4 style="margin-bottom: 12px; color: var(--gray-700);">${formatKey(key)}</h4>`;
            tableSection.appendChild(createDataTable(value));
            container.appendChild(tableSection);
        } else if (value && typeof value === 'object' && !('value' in value)) {
            // Check if it contains array fields (like financial_data containing equity, liabilities, assets, etc.)
            const subKeys = Object.keys(value);
            const arrayKeys = subKeys.filter(k => Array.isArray(value[k]));
            const nonArrayKeys = subKeys.filter(k => !Array.isArray(value[k]));

            if (arrayKeys.length > 0) {
                // It has tables to render!
                const groupSection = document.createElement('div');
                groupSection.style.marginTop = '24px';
                groupSection.innerHTML = `<h3 style="margin-bottom: 16px; border-bottom: 1px solid var(--gray-200); padding-bottom: 8px; color: var(--gray-800);">${formatKey(key)}</h3>`;
                
                // 1. Render table categories (e.g. Equity, Liabilities, Assets, Contingent Liabilities)
                for (const arrKey of arrayKeys) {
                    const subDiv = document.createElement('div');
                    subDiv.style.marginBottom = '24px';
                    subDiv.innerHTML = `<h4 style="margin-bottom: 10px; color: var(--primary);">${formatKey(arrKey)}</h4>`;
                    subDiv.appendChild(createDataTable(value[arrKey]));
                    groupSection.appendChild(subDiv);
                }

                // 2. Render totals or summaries (e.g. Total Assets, Total Capital & Liabilities)
                if (nonArrayKeys.length > 0) {
                    const totalsDiv = document.createElement('div');
                    totalsDiv.style.marginTop = '20px';
                    totalsDiv.innerHTML = `<h4 style="margin-bottom: 12px; color: var(--gray-700);">Summary & Totals</h4>`;
                    
                    const subGrid = document.createElement('div');
                    subGrid.className = 'kv-grid';
                    for (const nonArrKey of nonArrayKeys) {
                        const itemVal = value[nonArrKey];
                        if (itemVal === null || itemVal === undefined) continue;
                        
                        let dispSub = '';
                        if (typeof itemVal === 'object') {
                            dispSub = Object.entries(itemVal).map(([p, v]) => `<span style="background: var(--gray-100); border: 1px solid var(--gray-300); padding: 3px 8px; border-radius: 4px; font-size: 13px; margin-right: 8px; display: inline-block; margin-bottom: 4px;">${formatKey(p)}: <b>${v}</b></span>`).join('');
                        } else {
                            dispSub = itemVal;
                        }
                        
                        subGrid.innerHTML += `
                            <div class="kv-key">${formatKey(nonArrKey)}</div>
                            <div class="kv-value">${dispSub}</div>
                        `;
                    }
                    totalsDiv.appendChild(subGrid);
                    groupSection.appendChild(totalsDiv);
                }

                container.appendChild(groupSection);
            } else {
                // Pure nested key-value dictionary (e.g. metadata or standalone totals block)
                const groupSection = document.createElement('div');
                groupSection.style.marginTop = '24px';
                groupSection.innerHTML = `<h4 style="margin-bottom: 12px; color: var(--gray-700);">${formatKey(key)}</h4>`;
                
                const subGrid = document.createElement('div');
                subGrid.className = 'kv-grid';
                for (const [subK, subV] of Object.entries(value)) {
                    if (subV === null || subV === undefined) continue;
                    let dispSub = '';
                    if (typeof subV === 'object') {
                        dispSub = Object.entries(subV).map(([p, v]) => `<span style="background: var(--gray-100); border: 1px solid var(--gray-300); padding: 3px 8px; border-radius: 4px; font-size: 13px; margin-right: 8px; display: inline-block; margin-bottom: 4px;">${formatKey(p)}: <b>${v}</b></span>`).join('');
                    } else {
                        dispSub = subV;
                    }
                    subGrid.innerHTML += `
                        <div class="kv-key">${formatKey(subK)}</div>
                        <div class="kv-value">${dispSub}</div>
                    `;
                }
                groupSection.appendChild(subGrid);
                container.appendChild(groupSection);
            }
        } else {
            // If value is null, only show if it is an essential expected scalar, or omit if it's an optional subtotal
            if (value === null) {
                // Omit optional totals if not applicable in standard format
                continue;
            }
            hasSimpleFields = true;
            let displayVal = '';
            if (value && typeof value === 'object' && 'value' in value) {
                // It's a field object
                if (value.value === null) {
                    displayVal = '<span class="badge badge-warning">Missing</span>';
                } else {
                    let confHtml = '';
                    if (value.confidence !== undefined) {
                        const color = value.confidence < 0.8 ? 'var(--warning)' : 'var(--success)';
                        confHtml = `<span style="font-size: 11px; margin-left: 8px; color: ${color}; border: 1px solid ${color}; padding: 1px 4px; border-radius: 4px;">Conf: ${(value.confidence * 100).toFixed(0)}%</span>`;
                    }
                    let pageHtml = value.page_number ? `<span style="font-size: 11px; margin-left: 4px; color: var(--gray-500);">Page ${value.page_number}</span>` : '';
                    displayVal = `<span>${value.value}</span> ${confHtml} ${pageHtml}`;
                }
            } else if (typeof value === 'object') {
                displayVal = Object.entries(value).map(([p, v]) => `<span style="background: var(--gray-100); border: 1px solid var(--gray-300); padding: 3px 8px; border-radius: 4px; font-size: 13px; margin-right: 8px; display: inline-block; margin-bottom: 4px;">${formatKey(p)}: <b>${v}</b></span>`).join('');
            } else {
                displayVal = value;
            }
            
            fieldsGrid.innerHTML += `
                <div class="kv-key">${formatKey(key)}</div>
                <div class="kv-value">${displayVal}</div>
            `;
        }
    }
    
    if (hasSimpleFields) {
        container.insertBefore(fieldsGrid, container.firstChild);
    }
}

function createDataTable(items) {
    if (!items || items.length === 0) return document.createTextNode('No items found.');
    
    const wrapper = document.createElement('div');
    wrapper.style.overflowX = 'auto';
    
    const table = document.createElement('table');
    table.className = 'data-table';
    
    // Check if items have nested "values" dict (e.g. values: { "31-Mar-17": 5125, "31-Mar-16": 5056 })
    const allPeriodKeys = new Set();
    const hasValuesDict = items.some(item => item && item.values && typeof item.values === 'object' && !Array.isArray(item.values));
    if (hasValuesDict) {
        items.forEach(item => {
            if (item && item.values && typeof item.values === 'object') {
                Object.keys(item.values).forEach(p => allPeriodKeys.add(p));
            }
        });
    }

    // Collect standard keys
    const allKeys = new Set();
    items.forEach(item => {
        if (item && typeof item === 'object') {
            Object.keys(item).forEach(k => {
                if (k !== 'values') allKeys.add(k);
            });
        }
    });

    const standardHeaders = Array.from(allKeys);
    const periodHeaders = Array.from(allPeriodKeys);
    
    let thead = '<thead><tr>';
    standardHeaders.forEach(h => thead += `<th>${formatKey(h)}</th>`);
    periodHeaders.forEach(p => thead += `<th>${formatKey(p)}</th>`);
    thead += '</tr></thead>';
    
    let tbody = '<tbody>';
    items.forEach(item => {
        tbody += '<tr>';
        // Render standard fields
        standardHeaders.forEach(h => {
            let val = item[h];
            let displayVal = '';
            if (val && typeof val === 'object' && 'value' in val) {
                displayVal = val.value === null ? '<span style="color:var(--gray-400)">-</span>' : val.value;
            } else if (val === null || val === undefined) {
                displayVal = '<span style="color:var(--gray-400)">-</span>';
            } else if (typeof val === 'object') {
                displayVal = JSON.stringify(val);
            } else {
                displayVal = val;
            }
            tbody += `<td>${displayVal}</td>`;
        });
        
        // Render period values if present
        periodHeaders.forEach(p => {
            let pVal = item.values ? item.values[p] : null;
            let displayP = (pVal !== null && pVal !== undefined) ? pVal : '<span style="color:var(--gray-400)">-</span>';
            tbody += `<td><strong>${displayP}</strong></td>`;
        });

        tbody += '</tr>';
    });
    tbody += '</tbody>';
    
    table.innerHTML = thead + tbody;
    wrapper.appendChild(table);
    return wrapper;
}

function renderValidation(val) {
    const overall = document.getElementById('validation-overall');
    const overallStat = val.overall_status || val.status || 'PASS';
    const badgeClass = overallStat === 'PASS' ? 'badge-pass' : (overallStat === 'FAIL' ? 'badge-fail' : 'badge-gray');
    overall.innerHTML = `<strong>Overall Status:</strong> <span class="badge ${badgeClass}" style="font-size: 14px;">${overallStat}</span>`;
    
    if (val.issues && val.issues.length > 0) {
        const issuesDiv = document.getElementById('validation-issues');
        issuesDiv.innerHTML = `<div style="background: #fee2e2; border: 1px solid #f87171; padding: 12px; border-radius: var(--radius-sm); color: #991b1b;">
            <strong style="display:block; margin-bottom: 4px;">Issues found:</strong>
            <ul style="margin: 0; padding-left: 20px;">
                ${val.issues.map(i => `<li>${i}</li>`).join('')}
            </ul>
        </div>`;
    }
    
    const checksContainer = document.getElementById('validation-checks');
    checksContainer.innerHTML = '';
    
    if (val.checks && val.checks.length > 0) {
        val.checks.forEach(check => {
            const div = document.createElement('div');
            const status = check.status || 'PASS';
            const statusClass = status === 'PASS' ? 'pass' : (status === 'FAIL' ? 'fail' : 'na');
            const badgeClass = status === 'PASS' ? 'badge-pass' : (status === 'FAIL' ? 'badge-fail' : 'badge-gray');
            div.className = `validation-check ${statusClass}`;
            
            let operandsHtml = '';
            if (check.operands) {
                operandsHtml = Object.entries(check.operands).map(([k, v]) => `<span style="background: var(--gray-200); padding: 2px 6px; border-radius: 4px; font-size: 12px; margin-right: 8px;">${k}: <b>${v}</b></span>`).join('');
            }
            
            const checkTitle = check.name || check.check_id || 'Check';
            
            div.innerHTML = `
                <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
                    <strong style="color: var(--gray-900);">${formatKey(checkTitle)}</strong>
                    <span class="badge ${badgeClass}">${status}</span>
                </div>
                ${check.formula ? `<div style="font-size: 12px; color: var(--gray-600); font-family: monospace; margin-bottom: 8px;">Formula: ${check.formula}</div>` : ''}
                ${operandsHtml ? `<div style="margin-bottom: 8px;">${operandsHtml}</div>` : ''}
                <div style="display: flex; gap: 16px; font-size: 13px; color: var(--gray-700);">
                    <div>Calc: <b>${check.calculated_value !== null && check.calculated_value !== undefined ? check.calculated_value : '-'}</b></div>
                    <div>Reported: <b>${check.reported_value !== null && check.reported_value !== undefined ? check.reported_value : '-'}</b></div>
                    ${check.variance !== undefined && check.variance !== null ? `<div>Variance: <b>${(check.variance * 100).toFixed(2)}%</b></div>` : ''}
                </div>
                ${check.message ? `<div style="margin-top: 8px; font-size: 13px; color: ${status === 'FAIL' ? 'var(--danger)' : 'var(--gray-600)'};">${check.message}</div>` : ''}
            `;
            checksContainer.appendChild(div);
        });
    } else {
        checksContainer.innerHTML = '<p style="color: var(--gray-500); font-size: 14px;">No validation checks performed.</p>';
    }
}

function renderMetadata(meta) {
    const grid = document.getElementById('metadata-grid');
    grid.innerHTML = '';
    
    Object.entries(meta).forEach(([key, val]) => {
        grid.innerHTML += `
            <div class="kv-key">${formatKey(key)}</div>
            <div class="kv-value">${typeof val === 'boolean' ? (val ? 'Yes' : 'No') : val}</div>
        `;
    });
}

function renderRawJSON(data) {
    const wrapper = document.getElementById('json-wrapper');
    const pre = document.getElementById('raw-json');
    const toggleBtn = document.getElementById('toggle-json-btn');
    const copyBtn = document.getElementById('copy-json-btn');
    
    pre.textContent = JSON.stringify(data, null, 2);
    
    toggleBtn.addEventListener('click', () => {
        if (wrapper.style.display === 'none') {
            wrapper.style.display = 'block';
            toggleBtn.textContent = 'Hide Raw JSON';
        } else {
            wrapper.style.display = 'none';
            toggleBtn.textContent = 'View Raw JSON';
        }
    });

    copyBtn.addEventListener('click', () => {
        navigator.clipboard.writeText(pre.textContent).then(() => {
            const orig = copyBtn.textContent;
            copyBtn.textContent = 'Copied!';
            setTimeout(() => copyBtn.textContent = orig, 2000);
        });
    });
}

function formatKey(key) {
    return key.split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ');
}

function formatDocumentType(type) {
    if (!type) return 'Unknown';
    return type.split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ');
}

function formatDate(isoString) {
    if (!isoString) return 'N/A';
    const d = new Date(isoString);
    return d.toLocaleString();
}
