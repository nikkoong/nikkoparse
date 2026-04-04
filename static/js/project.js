/**
 * Project Page JavaScript - Redesigned
 */

let projectId = null;
let project = null;
let currentFile = null;
let selectedText = null;
let selectedTextPosition = null; // Store position of selected text in document
let selectedFields = [];
let allSuggestions = [];
let extractionResults = null;

document.addEventListener('DOMContentLoaded', () => {
  const path = window.location.pathname;
  projectId = path.split('/').pop();
  
  loadProject();
  setupEventListeners();
});

function setupEventListeners() {
  // Add Files Button
  document.getElementById('addFilesBtn').addEventListener('click', openUploadModal);
  
  // Project name editing
  const projectNameEl = document.getElementById('projectName');
  let originalName = '';
  
  projectNameEl.addEventListener('focus', () => {
    originalName = projectNameEl.textContent.trim();
  });
  
  projectNameEl.addEventListener('blur', async () => {
    const newName = projectNameEl.textContent.trim();
    if (newName !== originalName && newName.length > 0) {
      await renameProject(newName);
    } else if (newName.length === 0) {
      // Restore original name if user deleted everything
      projectNameEl.textContent = originalName;
    }
  });
  
  projectNameEl.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      projectNameEl.blur(); // Trigger save
    } else if (e.key === 'Escape') {
      e.preventDefault();
      projectNameEl.textContent = originalName;
      projectNameEl.blur();
    }
  });
  
  // Upload modal
  const uploadZone = document.getElementById('uploadZone');
  const fileInput = document.getElementById('fileInput');
  
  uploadZone.addEventListener('click', () => fileInput.click());
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
    const files = Array.from(e.dataTransfer.files).filter(f => f.name.endsWith('.pdf'));
    if (files.length > 0) handleFileUpload(files);
  });
  
  fileInput.addEventListener('change', (e) => {
    if (e.target.files.length > 0) {
      handleFileUpload(Array.from(e.target.files));
    }
  });
  
  // Text selection in document preview
  const preview = document.getElementById('documentPreview');
  preview.addEventListener('mouseup', handleTextSelection);
  preview.addEventListener('touchend', handleTextSelection);
  
  // Enter key to open modal when text is selected
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && selectedText && !isModalOpen()) {
      e.preventDefault();
      openFieldCreationModal();
    }
  });
  
  // Create Field button
  document.getElementById('createFieldBtn').addEventListener('click', openFieldCreationModal);
  
  // Suggest Fields
  document.getElementById('suggestFieldsBtn').addEventListener('click', showSuggestionsModal);
  
  // Run Extraction
  if (document.getElementById('runExtractionBtn')) {
    document.getElementById('runExtractionBtn').addEventListener('click', runExtraction);
  }
  
  // Export TSV
  if (document.getElementById('exportTsvBtn')) {
    document.getElementById('exportTsvBtn').addEventListener('click', exportToTSV);
  }
}

async function loadProject() {
  try {
    project = await api.getProject(projectId);
    document.getElementById('projectName').textContent = project.name;
    
    const fileCount = project.files ? project.files.length : 0;
    const parsed = project.files ? project.files.filter(f => f.parsed && !f.parse_failed).length : 0;
    document.getElementById('projectStats').textContent = 
      `${parsed} of ${fileCount} files parsed`;
    
    if (parsed > 0) {
      renderFilesList();
      document.getElementById('filesList').style.display = 'block';
      document.getElementById('viewerSection').style.display = 'block';
      
      // Load suggestions
      await loadSuggestions();
    }
    
    if (project.schema && project.schema.length > 0) {
      selectedFields = project.schema;
      renderExtractionTable();
    }
    
    if (project.last_extracted) {
      await loadResults();
    }
  } catch (error) {
    alert('Failed to load project: ' + error.message);
  }
}

async function renameProject(newName) {
  try {
    const result = await api.renameProject(projectId, newName);
    if (result.error) {
      alert('Failed to rename project: ' + result.error);
      // Restore original name
      document.getElementById('projectName').textContent = project.name;
    } else {
      // Update local project object
      project.name = newName;
      // Update document title
      document.title = `${newName} - NikkoParse`;
    }
  } catch (error) {
    alert('Failed to rename project: ' + error.message);
    // Restore original name
    document.getElementById('projectName').textContent = project.name;
  }
}

function renderFilesList() {
  const parsedFiles = project.files.filter(f => f.parsed && !f.parse_failed);
  const container = document.getElementById('filesListContainer');
  const dropdown = document.getElementById('filesDropdown');
  
  if (parsedFiles.length === 0) {
    container.innerHTML = '<p style="color:#666">No files uploaded yet</p>';
    dropdown.style.display = 'none';
    return;
  }
  
  // Use dropdown if more than 10 files
  if (parsedFiles.length > 10) {
    dropdown.style.display = 'block';
    container.innerHTML = ''; // Hide the file items list
    
    // Populate dropdown
    dropdown.innerHTML = '<option value="">Select a file...</option>' + 
      parsedFiles.map(f => 
        `<option value="${escapeHtml(f.filename)}" ${f.filename === currentFile ? 'selected' : ''}>
          ${escapeHtml(f.filename)}
        </option>`
      ).join('');
    
  } else {
    // Use traditional list view for 10 or fewer files
    dropdown.style.display = 'none';
    
    const html = parsedFiles.map(f => createFileItemHTML(f.filename)).join('');
    
    container.innerHTML = html;
  }
}

function selectFileFromDropdown(filename) {
  if (filename) {
    selectFile(filename);
  }
}

async function selectFile(filename) {
  try {
    // Update active state in list view
    document.querySelectorAll('.file-item').forEach(item => {
      item.classList.remove('active');
      if (item.querySelector('.file-name') && item.querySelector('.file-name').textContent === filename) {
        item.classList.add('active');
      }
    });
    
    // Update dropdown selection if visible
    const dropdown = document.getElementById('filesDropdown');
    if (dropdown.style.display !== 'none') {
      dropdown.value = filename;
    }
    
    // Load file text as markdown
    const result = await api.getFileText(projectId, filename);
    const preview = document.getElementById('documentPreview');
    preview.textContent = result.text;
    currentFile = filename;
    
    // Update extraction table with current file highlighted
    if (extractionResults) {
      renderExtractionTable();
    }
  } catch (error) {
    alert('Failed to load file: ' + error.message);
  }
}

function handleTextSelection() {
  const preview = document.getElementById('documentPreview');
  const selection = window.getSelection();
  const text = selection.toString().trim();
  const btn = document.getElementById('createFieldBtn');
  
  if (text && selection.rangeCount > 0) {
    selectedText = text;
    
    // Calculate position of selected text in the document
    const range = selection.getRangeAt(0);
    
    // Find character offset in the full document text
    const fullText = preview.textContent;
    const selectedIndex = fullText.indexOf(text);
    selectedTextPosition = selectedIndex >= 0 ? selectedIndex : null;
    
    // Get selection position relative to the preview container
    const rect = range.getBoundingClientRect();
    const previewContainer = preview.parentElement; // .preview-container
    const containerRect = previewContainer.getBoundingClientRect();
    
    // Calculate Y position relative to the container (works across zoom levels)
    // Use the vertical center of the selection
    const selectionCenterY = rect.top + (rect.height / 2);
    const relativeY = selectionCenterY - containerRect.top;
    
    // Account for scroll position of the preview
    // The sidebar doesn't scroll, so we need to check if the selection is visible
    const previewScrollTop = preview.scrollTop;
    const previewRect = preview.getBoundingClientRect();
    
    // Calculate the visible area boundaries
    const visibleTop = 0;
    const visibleBottom = containerRect.height;
    
    // Clamp the button position to stay within visible bounds
    const buttonSize = 28;
    const padding = 5;
    let buttonTop = relativeY - (buttonSize / 2);
    buttonTop = Math.max(padding, Math.min(buttonTop, visibleBottom - buttonSize - padding));
    
    btn.style.top = buttonTop + 'px';
    btn.style.display = 'flex';
  } else {
    selectedText = null;
    selectedTextPosition = null;
    btn.style.display = 'none';
  }
}

function openFieldCreationModal() {
  if (!selectedText) {
    alert('Please select text in the document preview first');
    return;
  }
  
  const modal = document.getElementById('fieldModal');
  const labelInput = document.getElementById('fieldLabel');
  const datalist = document.getElementById('existingLabels');
  const hintEl = document.getElementById('existingLabelHint');
  const existingExamplesGroup = document.getElementById('existingExamplesGroup');
  
  // Reset modal state
  labelInput.value = '';
  document.getElementById('selectedValue').value = selectedText;
  document.getElementById('selectedValueGroup').style.display = 'block';
  hintEl.style.display = 'none';
  existingExamplesGroup.style.display = 'none';
  document.getElementById('fieldModalTitle').textContent = 'Add Field Example';
  document.getElementById('saveFieldBtn').textContent = 'Add Example';
  
  // Populate datalist with existing labels
  datalist.innerHTML = '';
  const existingLabels = selectedFields.map(f => f.label);
  existingLabels.forEach(label => {
    const option = document.createElement('option');
    option.value = label;
    datalist.appendChild(option);
  });
  
  // Add event listener to detect when user selects existing label
  labelInput.oninput = () => {
    const normalizedInput = normalizeLabel(labelInput.value);
    const existingField = selectedFields.find(f => normalizeLabel(f.label) === normalizedInput);
    
    if (existingField) {
      hintEl.style.display = 'block';
      existingExamplesGroup.style.display = 'block';
      
      // Show existing examples for this field
      const examplesList = document.getElementById('existingExamplesList');
      const examples = existingField.examples || [];
      
      if (examples.length > 0) {
        examplesList.innerHTML = examples.map((ex, idx) => `
          <div style="padding:5px 0;border-bottom:1px solid #eee">
            <strong>${idx + 1}.</strong> "${escapeHtml(ex.value)}" 
            <span style="color:#888;font-size:12px">from ${escapeHtml(ex.file)}</span>
          </div>
        `).join('');
      } else if (existingField.example_value) {
        // Legacy single example
        examplesList.innerHTML = `
          <div style="padding:5px 0">
            <strong>1.</strong> "${escapeHtml(existingField.example_value)}" 
            <span style="color:#888;font-size:12px">from ${escapeHtml(existingField.example_file || 'unknown')}</span>
          </div>
        `;
      } else {
        examplesList.innerHTML = '<em style="color:#888">No examples yet</em>';
      }
    } else {
      hintEl.style.display = 'none';
      existingExamplesGroup.style.display = 'none';
    }
  };
  
  // Add Enter key handler to submit the form
  labelInput.onkeydown = (e) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      saveNewField();
    }
  };
  
  modal.style.display = 'flex';
  labelInput.focus();
}

/**
 * Normalize a label for comparison (lowercase, trimmed)
 */
function normalizeLabel(label) {
  return label.toLowerCase().trim().replace(/\s+/g, ' ');
}

function closeFieldModal() {
  document.getElementById('fieldModal').style.display = 'none';
}

async function saveNewField() {
  const rawLabel = document.getElementById('fieldLabel').value.trim();
  
  if (!rawLabel) {
    alert('Please enter a field label');
    return;
  }
  
  // Normalize the label for storage (trim and normalize whitespace, preserve original case for display)
  const displayLabel = rawLabel.replace(/\s+/g, ' ');
  const normalizedLabel = normalizeLabel(rawLabel);
  
  // Get context around selected text for better AI prompt
  const preview = document.getElementById('documentPreview');
  const fullText = preview.textContent;
  const selectedIndex = selectedTextPosition !== null ? selectedTextPosition : fullText.indexOf(selectedText);
  
  // Get 500 characters before and after the selection for context
  const contextStart = Math.max(0, selectedIndex - 500);
  const contextEnd = Math.min(fullText.length, selectedIndex + selectedText.length + 500);
  const contextText = fullText.substring(contextStart, contextEnd);
  
  // Create example object
  const example = {
    value: selectedText,
    file: currentFile,
    context: contextText,
    position: selectedIndex
  };
  
  // Check if field with this label already exists (case-insensitive comparison)
  const existingFieldIndex = selectedFields.findIndex(f => normalizeLabel(f.label) === normalizedLabel);
  
  if (existingFieldIndex >= 0) {
    // Add example to existing field
    const existingField = selectedFields[existingFieldIndex];
    
    // Initialize examples array if not present
    if (!existingField.examples) {
      existingField.examples = [];
      // Migrate legacy single example if present
      if (existingField.example_value) {
        existingField.examples.push({
          value: existingField.example_value,
          file: existingField.example_file || 'unknown',
          context: existingField.example_context || '',
          position: null
        });
      }
    }
    
    // Check if this exact example already exists (same value from same file)
    const duplicateExample = existingField.examples.find(
      ex => ex.value === example.value && ex.file === example.file
    );
    
    if (duplicateExample) {
      alert('This exact example already exists for this field.');
      return;
    }
    
    // Add the new example
    existingField.examples.push(example);
    
    // Update manual_values for this file
    if (!existingField.manual_values) {
      existingField.manual_values = {};
    }
    existingField.manual_values[currentFile] = selectedText;
    
    // Keep legacy fields updated for backward compatibility
    if (!existingField.example_value) {
      existingField.example_value = selectedText;
      existingField.example_file = currentFile;
      existingField.example_context = contextText;
    }
  } else {
    // Create new field with the example
    const field = {
      field_id: displayLabel.toLowerCase().replace(/\s+/g, '_'),
      label: displayLabel,
      example_value: selectedText,
      example_context: contextText,
      example_file: currentFile,
      examples: [example],
      regex: null,
      manual_values: {}
    };
    
    // Add manual value for current file
    field.manual_values[currentFile] = selectedText;
    
    selectedFields.push(field);
  }
  
  // Save schema
  try {
    await api.saveSchema(projectId, selectedFields);
    closeFieldModal();
    renderExtractionTable();
    
    // Clear selection
    window.getSelection().removeAllRanges();
    selectedText = null;
    selectedTextPosition = null;
    document.getElementById('createFieldBtn').style.display = 'none';
  } catch (error) {
    alert('Failed to save field: ' + error.message);
  }
}

function renderExtractionTable() {
  const container = document.getElementById('extractionTableSection');
  const tableContainer = document.getElementById('tableContainer');
  
  if (selectedFields.length === 0) {
    container.style.display = 'none';
    return;
  }
  
  container.style.display = 'block';
  
  const parsedFiles = project.files.filter(f => f.parsed && !f.parse_failed);
  
  // Create table
  let html = '<table class="extraction-table"><thead><tr>';
  html += '<th>File</th>';
  selectedFields.forEach((field, idx) => {
    const dataType = field.value_type || detectDataType(field);
    const badgeClass = dataType === 'money' ? 'money' : dataType === 'date' ? 'date' : dataType === 'number' ? 'number' : 'text';
    html += `<th class="field-header" data-field-idx="${idx}">`;
    
    // Wrap content in a flex container
    html += `<div class="field-header-content">`;
    
    // Drag handle
    html += `<span class="drag-handle" title="Drag to reorder">⋮⋮</span>`;
    
    // Field label (clickable to view regex)
    html += `<span class="field-label" onclick="showFieldRegex(${idx})" title="Click to view regex">`;
    html += `${escapeHtml(field.label)}`;
    html += `<span class="data-type-badge ${badgeClass}">${dataType}</span>`;
    html += `</span>`;
    
    // Delete button
    html += `<button class="delete-field-btn" onclick="event.stopPropagation(); deleteField(${idx})" title="Delete field">×</button>`;
    
    html += `</div>`; // Close field-header-content
    html += `</th>`;
  });
  html += '</tr></thead><tbody>';
  
  parsedFiles.forEach(file => {
    const isCurrentFile = file.filename === currentFile;
    html += `<tr ${isCurrentFile ? 'style="background:var(--accent-orange-light)"' : ''}>`;
    html += `<td class="file-cell">${escapeHtml(file.filename)}</td>`;
    
    selectedFields.forEach(field => {
      const value = getCellValue(file.filename, field);
      const rawValue = getRawCellValue(file.filename, field);
      const isManual = field.manual_values && field.manual_values[file.filename];
      const isEmpty = !value && !rawValue;
      const cssClass = isEmpty ? 'empty-cell' : (isManual ? 'manual-value' : 'extracted-value');
      
      // Cell with kebab menu on hover (only for non-empty cells)
      if (isEmpty) {
        html += `<td class="${cssClass}">`;
        html += '<span style="color:var(--gray-400)">—</span>';
        html += '</td>';
      } else {
        html += `<td class="${cssClass}" onclick="navigateToValue('${escapeHtml(file.filename)}', '${escapeHtml(field.field_id)}', '${escapeHtml(rawValue || '').replace(/'/g, "\\'")}')">`;
        html += `<span class="cell-value">${value}</span>`;
        if (isManual) {
          html += ' <span style="color:var(--accent-orange);font-size:10px">✎</span>';
        }
        // Kebab menu button
        html += `<span class="cell-kebab" onclick="event.stopPropagation(); openCellEditor('${escapeHtml(file.filename)}', '${escapeHtml(field.field_id)}', '${escapeHtml(rawValue || '').replace(/'/g, "\\'")}')" title="Edit value">⋮</span>`;
        html += '</td>';
      }
    });
    
    html += '</tr>';
  });
  
  html += '</tbody></table>';
  tableContainer.innerHTML = html;
  
  // Initialize drag-and-drop for field headers
  initFieldDragAndDrop();
}

/**
 * Delete a field from the schema
 */
async function deleteField(fieldIdx) {
  const field = selectedFields[fieldIdx];
  
  if (!confirm(`Delete field "${field.label}"?\n\nThis will remove the field from the schema and all extraction results.`)) {
    return;
  }
  
  try {
    // Remove field from array
    selectedFields.splice(fieldIdx, 1);
    
    // Save updated schema
    await api.saveSchema(projectId, selectedFields);
    project.schema = selectedFields;
    
    // Re-render table
    renderExtractionTable();
    
    // Re-run extraction if there are still fields
    if (selectedFields.length > 0) {
      await api.runExtraction(projectId);
      await loadResults();
      renderExtractionTable();
    }
  } catch (error) {
    alert('Failed to delete field: ' + error.message);
  }
}

/**
 * Initialize drag-and-drop for field column reordering
 */
function initFieldDragAndDrop() {
  const headers = document.querySelectorAll('.field-header');
  let draggedIdx = null;
  
  headers.forEach((header, idx) => {
    const dragHandle = header.querySelector('.drag-handle');
    
    // Make the header draggable via the handle
    dragHandle.addEventListener('mousedown', (e) => {
      header.setAttribute('draggable', 'true');
      draggedIdx = idx;
    });
    
    header.addEventListener('dragstart', (e) => {
      e.dataTransfer.effectAllowed = 'move';
      header.classList.add('dragging');
    });
    
    header.addEventListener('dragend', (e) => {
      header.setAttribute('draggable', 'false');
      header.classList.remove('dragging');
      
      // Remove all drag-over classes
      headers.forEach(h => h.classList.remove('drag-over'));
    });
    
    header.addEventListener('dragover', (e) => {
      e.preventDefault();
      e.dataTransfer.dropEffect = 'move';
      
      if (draggedIdx !== null && draggedIdx !== idx) {
        header.classList.add('drag-over');
      }
    });
    
    header.addEventListener('dragleave', (e) => {
      header.classList.remove('drag-over');
    });
    
    header.addEventListener('drop', async (e) => {
      e.preventDefault();
      header.classList.remove('drag-over');
      
      if (draggedIdx !== null && draggedIdx !== idx) {
        // Reorder the fields array
        const draggedField = selectedFields[draggedIdx];
        selectedFields.splice(draggedIdx, 1);
        
        // Adjust target index if we removed an element before it
        const newIdx = draggedIdx < idx ? idx - 1 : idx;
        selectedFields.splice(newIdx, 0, draggedField);
        
        // Save and re-render
        try {
          await api.saveSchema(projectId, selectedFields);
          project.schema = selectedFields;
          renderExtractionTable();
        } catch (error) {
          alert('Failed to reorder fields: ' + error.message);
        }
      }
      
      draggedIdx = null;
    });
  });
}

/**
 * Detect the data type based on example values
 */
function detectDataType(field) {
  // Get example values to analyze
  const examples = [];
  
  if (field.examples && field.examples.length > 0) {
    field.examples.forEach(ex => examples.push(ex.value));
  } else if (field.example_value) {
    examples.push(field.example_value);
  }
  
  // Check manual values too
  if (field.manual_values) {
    Object.values(field.manual_values).forEach(v => examples.push(v));
  }
  
  if (examples.length === 0) return 'text';
  
  // Analyze patterns
  const moneyPattern = /^\$?[\d,]+\.?\d*$|^\$[\d,.]+$/;
  const datePattern = /^\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4}$|^\d{4}[\/\-]\d{1,2}[\/\-]\d{1,2}$|^(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)/i;
  const numberPattern = /^[\d,]+\.?\d*$|^\d+$/;
  
  let moneyCount = 0;
  let dateCount = 0;
  let numberCount = 0;
  
  examples.forEach(val => {
    if (!val) return;
    const trimmed = val.trim();
    
    // Check for money (has $ or looks like currency)
    if (trimmed.includes('$') || moneyPattern.test(trimmed)) {
      moneyCount++;
    }
    // Check for date
    else if (datePattern.test(trimmed)) {
      dateCount++;
    }
    // Check for pure number
    else if (numberPattern.test(trimmed)) {
      numberCount++;
    }
  });
  
  const total = examples.length;
  
  // Determine type based on majority
  if (moneyCount / total >= 0.5) return 'money';
  if (dateCount / total >= 0.5) return 'date';
  if (numberCount / total >= 0.5) return 'number';
  
  return 'text';
}

/**
 * Detect data type based on field label keywords
 */
function detectDataTypeFromLabel(label) {
  const lowerLabel = label.toLowerCase();
  
  // Money keywords
  const moneyKeywords = ['amount', 'price', 'cost', 'fee', 'charge', 'total', 'balance', 'payment', 'tax', 'subtotal', 'discount', 'credit', 'debit', 'rate', 'bill'];
  for (const keyword of moneyKeywords) {
    if (lowerLabel.includes(keyword)) return 'money';
  }
  
  // Date keywords
  const dateKeywords = ['date', 'due', 'issued', 'created', 'period', 'from', 'to', 'start', 'end', 'expir'];
  for (const keyword of dateKeywords) {
    if (lowerLabel.includes(keyword)) return 'date';
  }
  
  // Number keywords
  const numberKeywords = ['number', 'count', 'quantity', 'qty', 'units', 'days', 'kwh', 'usage', 'consumption', 'volume'];
  for (const keyword of numberKeywords) {
    if (lowerLabel.includes(keyword)) return 'number';
  }
  
  return null; // Let detectDataType handle it
}


function getCellValue(filename, field) {
  // First check for manual value
  if (field.manual_values && field.manual_values[filename]) {
    return escapeHtml(field.manual_values[filename]);
  }
  
  // Then check for extracted value
  if (!extractionResults || !extractionResults.results) return null;
  
  const fileResult = extractionResults.results.find(r => r.filename === filename);
  if (!fileResult || !fileResult.fields) return null;
  
  const fieldData = fileResult.fields[field.field_id];
  if (!fieldData) return null;
  
  // Return the primary extracted value (best match is already selected by backend)
  return fieldData.value ? escapeHtml(fieldData.value) : null;
}

/**
 * Get raw (unescaped) cell value for editing
 */
function getRawCellValue(filename, field) {
  // First check for manual value
  if (field.manual_values && field.manual_values[filename]) {
    return field.manual_values[filename];
  }
  
  // Then check for extracted value
  if (!extractionResults || !extractionResults.results) return '';
  
  const fileResult = extractionResults.results.find(r => r.filename === filename);
  if (!fileResult || !fileResult.fields) return '';
  
  const fieldData = fileResult.fields[field.field_id];
  if (!fieldData) return '';
  
  return fieldData.value || '';
}

/**
 * Open modal to edit a cell value
 */
function openCellEditor(filename, fieldId, currentValue) {
  const field = selectedFields.find(f => f.field_id === fieldId);
  if (!field) return;
  
  const modal = document.getElementById('cellEditorModal');
  document.getElementById('cellEditorFilename').textContent = filename;
  document.getElementById('cellEditorFieldname').textContent = field.label;
  document.getElementById('cellEditorInput').value = currentValue;
  
  // Store context for save
  modal.dataset.filename = filename;
  modal.dataset.fieldId = fieldId;
  
  // Check if there's a manual override
  const hasOverride = field.manual_values && field.manual_values[filename];
  document.getElementById('cellEditorClearBtn').style.display = hasOverride ? 'inline-block' : 'none';
  
  modal.style.display = 'flex';
  document.getElementById('cellEditorInput').focus();
  document.getElementById('cellEditorInput').select();
}

/**
 * Save the edited cell value as a manual override
 */
async function saveCellEdit() {
  const modal = document.getElementById('cellEditorModal');
  const filename = modal.dataset.filename;
  const fieldId = modal.dataset.fieldId;
  const newValue = document.getElementById('cellEditorInput').value.trim();
  
  const field = selectedFields.find(f => f.field_id === fieldId);
  if (!field) return;
  
  // Initialize manual_values if needed
  if (!field.manual_values) {
    field.manual_values = {};
  }
  
  // Set the manual override
  if (newValue) {
    field.manual_values[filename] = newValue;
  } else {
    // Empty value clears the override
    delete field.manual_values[filename];
  }
  
  // Save schema to persist the override
  try {
    await api.saveSchema(projectId, selectedFields);
    project.schema = selectedFields;
    renderExtractionTable();
    closeCellEditor();
  } catch (error) {
    alert('Failed to save: ' + error.message);
  }
}

/**
 * Clear the manual override and revert to extracted value
 */
async function clearCellOverride() {
  const modal = document.getElementById('cellEditorModal');
  const filename = modal.dataset.filename;
  const fieldId = modal.dataset.fieldId;
  
  const field = selectedFields.find(f => f.field_id === fieldId);
  if (!field || !field.manual_values) return;
  
  // Remove the manual override
  delete field.manual_values[filename];
  
  // Save schema
  try {
    await api.saveSchema(projectId, selectedFields);
    project.schema = selectedFields;
    renderExtractionTable();
    closeCellEditor();
  } catch (error) {
    alert('Failed to save: ' + error.message);
  }
}

/**
 * Close the cell editor modal
 */
function closeCellEditor() {
  document.getElementById('cellEditorModal').style.display = 'none';
}

async function loadSuggestions() {
  try {
    const result = await api.getSuggestions(projectId);
    allSuggestions = result.suggestions || [];
  } catch (error) {
    console.error('Failed to load suggestions:', error);
  }
}

function showSuggestionsModal() {
  if (allSuggestions.length === 0) {
    alert('No field suggestions available. Make sure you have uploaded and parsed files.');
    return;
  }
  
  const modal = document.getElementById('suggestionsModal');
  const list = document.getElementById('suggestionsList');
  
  let html = allSuggestions.map((s, idx) => `
    <div class="suggestion-item">
      <input type="checkbox" id="suggest_${idx}" value="${idx}">
      <label for="suggest_${idx}" class="suggestion-label">${escapeHtml(s.label)}</label>
      <span class="suggestion-regex">${escapeHtml(s.suggested_regex || 'No regex')}</span>
    </div>
  `).join('');
  
  list.innerHTML = html;
  modal.style.display = 'flex';
}

function closeSuggestionsModal() {
  document.getElementById('suggestionsModal').style.display = 'none';
}

async function addSelectedSuggestions() {
  const checkboxes = document.querySelectorAll('#suggestionsList input[type="checkbox"]:checked');
  
  if (checkboxes.length === 0) {
    alert('Please select at least one field');
    return;
  }
  
  checkboxes.forEach(cb => {
    const idx = parseInt(cb.value);
    const suggestion = allSuggestions[idx];
    
    // Check if field already exists
    if (!selectedFields.some(f => f.label.toLowerCase() === suggestion.label.toLowerCase())) {
      selectedFields.push({
        field_id: suggestion.field_id,
        label: suggestion.label,
        regex: suggestion.suggested_regex,
        suggested: true
      });
    }
  });
  
  // Save schema
  try {
    await api.saveSchema(projectId, selectedFields);
    closeSuggestionsModal();
    renderExtractionTable();
  } catch (error) {
    alert('Failed to add fields: ' + error.message);
  }
}

/**
 * Generate pattern hints by analyzing the context before a field value
 * 
 * Detects structural elements and suggests regex building blocks:
 * - Row labels (words/phrases before the value)
 * - Date patterns to skip (e.g., "12/21/2025 - 01/03/2026")
 * - Number columns to skip (e.g., "80")
 * 
 * @param {string} beforeText - Text before the value (200-500 chars)
 * @param {string} value - The field value to extract
 * @param {string} fieldType - Data type (money|date|number|text)
 * @returns {object} Pattern hints with building blocks and suggestions
 */
/**
 * Generate regex pattern hints from context and example value
 * 
 * This is the core pattern generation algorithm that analyzes the context
 * around a selected value and generates flexible, context-aware regex patterns.
 * 
 * @param {string} beforeText - Text before the value (up to 750 chars)
 * @param {string} value - The example value to capture
 * @param {string} fieldType - Data type: 'money', 'date', 'number', or 'text'
 * @returns {Object} hints object containing building blocks and suggested patterns
 * 
 * @example
 * const hints = generatePatternHint(
 *   "401(k) Basic Contribution     ",
 *   "50.00",
 *   "money"
 * );
 * // Returns 3 patterns: specific, medium, fallback
 */
function generatePatternHint(beforeText, value, fieldType) {
  const hints = {
    buildingBlocks: [],
    suggestedPatterns: [],
    explanation: ''
  };
  
  // Take last 200 chars for analysis (focus on immediate context)
  const contextWindow = beforeText.slice(-200).trim();
  
  // Extract the last line/row (most likely contains the label and columns)
  const lines = contextWindow.split('\n');
  const lastLine = lines[lines.length - 1] || '';
  
  // 1. Detect row label (word or phrase at the start of the last line)
  // Look for words/text before numbers/dates
  // Enhanced to detect full phrases and create flexible patterns
  const trimmedLine = lastLine.trim();
  
  let rowLabel = null;
  let flexiblePattern = null; // Pattern with numbers replaced by regex patterns
  
  // --- LABEL DETECTION STRATEGIES ---
  
  // Strategy 1: If line ends with special chars like @ or :, capture the whole line
  // This handles patterns like "Supply 2.00 therms @" or "Account:"
  if (/[@:]$/.test(trimmedLine)) {
    rowLabel = trimmedLine;
  }
  // Strategy 2: Match label before 2+ spaces (standard column separator)
  else {
    const labelMatch = trimmedLine.match(/^([A-Za-z0-9][A-Za-z0-9\s()/-]*?)(?=\s{2,})/);
    if (labelMatch) {
      rowLabel = labelMatch[1].trim();
    }
    // Strategy 3: Fallback - if no 2+ spaces and line doesn't end with digit/currency, use whole line
    else if (!/[\d$¢]$/.test(trimmedLine)) {
      rowLabel = trimmedLine;
    }
  }
  
  if (rowLabel) {
    // --- FLEXIBLE PATTERN GENERATION ---
    // Two-step process to avoid double-escaping:
    // Step 1: Escape regex special characters
    let escapedLabel = rowLabel.replace(/[()[\]{}.*+?^$|\\]/g, '\\$&');
    
    // Step 2: Replace specific numbers with flexible patterns
    // Example: "Supply 2\.00 therms @" → "Supply \\d+(?:\\.\\d+)? therms @"
    // This allows matching any amount (1.00, 2.00, 3.50) while keeping distinctive words
    flexiblePattern = escapedLabel.replace(/\d+(?:\\\.\d+)?/g, '\\d+(?:\\.\\d+)?');
    
    hints.buildingBlocks.push({
      type: 'label',
      pattern: flexiblePattern,
      description: `Row label: "${rowLabel}" (flexible)`,
      originalLabel: rowLabel
    });
  }
  
  // 2. Detect date patterns (common formats: MM/DD/YYYY, ranges with -)
  const datePattern = /\d{1,2}\/\d{1,2}\/\d{4}(\s*-\s*\d{1,2}\/\d{1,2}\/\d{4})?/g;
  const dates = [];
  const datePositions = [];
  let dateMatch;
  
  while ((dateMatch = datePattern.exec(lastLine)) !== null) {
    dates.push(dateMatch[0]);
    datePositions.push({
      start: dateMatch.index,
      end: dateMatch.index + dateMatch[0].length
    });
  }
  
  if (dates.length > 0) {
    hints.buildingBlocks.push({
      type: 'skip_date',
      pattern: '\\d{1,2}/\\d{1,2}/\\d{4}(?:\\s*-\\s*\\d{1,2}/\\d{1,2}/\\d{4})?',
      description: `Skip date column: "${dates[0]}"`,
      example: dates[0]
    });
  }
  
  // 3. Detect number columns to skip (standalone numbers before the target value)
  // --- IMPORTANT: Exclude numbers that are part of dates or labels ---
  const numbers = [];
  const numberPattern = /\d+(?:\.\d+)?/g;
  let numMatch;
  
  // Calculate label end position if we have a label
  // This is critical for Bug Fix #1: prevents "401" in "401(k)" from being treated as skip number
  let labelEndPos = 0;
  if (rowLabel) {
    labelEndPos = lastLine.indexOf(rowLabel) + rowLabel.length;
  }
  
  while ((numMatch = numberPattern.exec(lastLine)) !== null) {
    const numText = numMatch[0];
    const numPos = numMatch.index;
    
    // Skip if this number is the target value
    if (numText === value || value.includes(numText)) {
      continue;
    }
    
    // Skip if this number is within a date range
    const isInDate = datePositions.some(d => numPos >= d.start && numPos < d.end);
    if (isInDate) {
      continue;
    }
    
    // --- BUG FIX #1: Skip if this number is part of the label ---
    // Example: "401" in "401(k) Basic Contribution"
    // Without this check, "401" would be treated as a skip pattern, causing
    // the pattern to skip over the actual value we want to capture
    if (labelEndPos > 0 && numPos < labelEndPos) {
      continue;
    }
    
    numbers.push(numText);
  }
  
  // Add unique numbers to building blocks
  const uniqueNumbers = [...new Set(numbers)];
  uniqueNumbers.forEach(num => {
    hints.buildingBlocks.push({
      type: 'skip_number',
      pattern: '\\d+(?:\\.\\d+)?',
      description: `Skip number column: "${num}"`,
      example: num
    });
  });
  
  // 4. Generate suggested patterns based on building blocks
  const valuePattern = getValuePattern(value, fieldType);
  
  if (hints.buildingBlocks.length > 0) {
    const labelBlock = hints.buildingBlocks.find(b => b.type === 'label');
    const dateBlocks = hints.buildingBlocks.filter(b => b.type === 'skip_date');
    const numberBlocks = hints.buildingBlocks.filter(b => b.type === 'skip_number');
    
    // Pattern 1: Specific (label + skip date + skip ONE number if exists)
    if (labelBlock) {
      const parts = [labelBlock.pattern];
      let explanation = [`match "${labelBlock.description.replace('Row label: "', '').replace('"', '')}"`];
      
      // Add date skip if exists
      if (dateBlocks.length > 0) {
        parts.push(dateBlocks[0].pattern);
        explanation.push('skip date');
      }
      
      // Add ONLY ONE number skip if exists (usually the hours/quantity column)
      if (numberBlocks.length > 0) {
        parts.push('\\d+(?:\\.\\d+)?');
        explanation.push(`skip number`);
      }
      
      const specificPattern = parts.join('\\s+') + '\\s+' + valuePattern;
      hints.suggestedPatterns.push({
        priority: 1,
        type: 'specific',
        pattern: specificPattern,
        explanation: explanation.join(' → ') + ` → capture ${fieldType}`
      });
      
      // Pattern 2: Medium (label + greedy skip to value)
      const escapedLabel = labelBlock.pattern;
      const mediumPattern = escapedLabel + '.*?' + valuePattern;
      hints.suggestedPatterns.push({
        priority: 2,
        type: 'medium',
        pattern: mediumPattern,
        explanation: `Match label then skip to ${fieldType}`
      });
    }
  }
  
  // Pattern 3: Fallback (value-only pattern)
  hints.suggestedPatterns.push({
    priority: 3,
    type: 'value_only',
    pattern: valuePattern,
    explanation: `Match any ${fieldType} value (fallback)`
  });
  
  return hints;
}

/**
 * Get regex pattern for capturing a value based on its type
 * 
 * @param {string} value - The value example
 * @param {string} fieldType - Data type (money|date|number|text)
 * @returns {string} Regex pattern with capture group
 */
function getValuePattern(value, fieldType) {
  switch (fieldType) {
    case 'money':
      // Check for price with unit (e.g., "58.500¢/therm", "12.50¢/kWh")
      // Use flexible matching for the numeric part but keep the unit specific
      if (/[\d,\.]+¢\/[a-z]+/i.test(value)) {
        const unitMatch = value.match(/¢\/([a-z]+)/i);
        const unit = unitMatch ? unitMatch[1] : '[a-zA-Z]+';
        return `([\\d,\\.]+¢/${unit})`;
      }
      // Check if value includes $ symbol
      if (value.includes('$')) {
        return '(\\$[\\d,\\.]+)';
      }
      // Check if value includes units like "kWh", "therms", etc.
      // Keep the unit specific for better matching
      const unitsMatch = value.match(/[\d,\.]+ ?([a-zA-Z]+)/);
      if (unitsMatch) {
        const unit = unitsMatch[1];
        return `([\\d,\\.]+ ${unit})`;
      }
      return '([\\d,\\.]+)';
    
    case 'number':
      // Check for number with dashes (e.g., account numbers like "89613-14560-9")
      if (value.includes('-')) {
        return '([\\d-]+)';
      }
      // Check if value has decimals
      if (value.includes('.')) {
        return '([\\d,\\.]+)';
      }
      return '(\\d+)';
    
    case 'date':
      // Check if the value contains a date range (e.g., "01/04/2026 - 01/17/2026")
      if (/-/.test(value) && value.split('-').length === 2) {
        // Date range pattern that ALSO matches single dates (range is optional)
        // This pattern matches: "12/21/2025" OR "01/04/2026 - 01/17/2026"
        return '(\\d{1,2}/\\d{1,2}/\\d{2,4}(?:\\s*-\\s*\\d{1,2}/\\d{1,2}/\\d{2,4})?)';
      }
      // Single date format
      return '(\\d{1,2}/\\d{1,2}/\\d{2,4})';
    
    case 'text':
    default:
      // For text, capture word characters and spaces
      return '([A-Za-z0-9\\s]+)';
  }
}

/**
 * Auto-generate schema patterns directly from field examples
 * Skips AI entirely and uses deterministic pattern generation
 * 
 * This function orchestrates the entire auto-generate workflow:
 * 1. Validates fields and parsed files exist
 * 2. Smart example selection (prefers date ranges, longer values)
 * 3. Loads document texts for files with examples
 * 4. Generates patterns using generatePatternHint()
 * 5. Saves schema and runs extraction
 * 
 * @returns {Promise<void>}
 */
async function autoGenerateSchema() {
  try {
    if (!selectedFields || selectedFields.length === 0) {
      alert('No fields available. Please add fields first.');
      return;
    }
    
    // Confirm action
    if (!confirm('This will auto-generate regex patterns for all fields and run extraction. Continue?')) {
      return;
    }
    
    // Load parsed files
    const parsedFiles = project.files.filter(f => f.parsed && !f.parse_failed);
    if (parsedFiles.length === 0) {
      alert('No parsed files available');
      return;
    }
    
    // Collect all files that have examples
    const filesWithExamples = new Set();
    for (const field of selectedFields) {
      if (field.examples && field.examples.length > 0) {
        field.examples.forEach(ex => {
          if (ex.file) filesWithExamples.add(ex.file);
        });
      } else if (field.example_file) {
        filesWithExamples.add(field.example_file);
      }
    }
    
    if (filesWithExamples.size === 0) {
      alert('No field examples found. Please add example values by selecting text in the document viewer first.');
      return;
    }
    
    // Load text for all files with examples
    const fileTexts = {};
    for (const filename of filesWithExamples) {
      if (!filename) continue; // Skip undefined/null filenames
      try {
        const result = await api.getFileText(projectId, filename);
        fileTexts[filename] = result.text;
      } catch (e) {
        console.error(`Failed to load ${filename}:`, e);
        alert(`Failed to load file text for ${filename}. Please try again.`);
        return;
      }
    }
    
    if (Object.keys(fileTexts).length === 0) {
      alert('Failed to load any file text. Please check that files are properly parsed.');
      return;
    }
    
    // Generate patterns for each field
    const generatedSchema = [];
    
    for (const field of selectedFields) {
      let exampleValue = null;
      let exampleFile = null;
      
      // Get example value - prioritize the most complex/informative example
      if (field.examples && field.examples.length > 0) {
        // --- SMART EXAMPLE SELECTION STRATEGY ---
        // For dates: prefer date ranges over single dates
        // For other types: prefer longer/more complex values
        let bestExample = field.examples[0];
        
        const fieldType = detectDataTypeFromLabel(field.label) || detectDataType(field) || 'text';
        
        if (fieldType === 'date' && field.examples.length > 1) {
          // For dates, prefer examples with ranges (contain " - ")
          // Why: Range patterns with optional second date also match single dates
          // Example: pattern for "01/04/2026 - 01/17/2026" also matches "12/21/2025"
          const rangeExample = field.examples.find(ex => ex.value && ex.value.includes(' - '));
          if (rangeExample) {
            bestExample = rangeExample;
          }
        } else if (field.examples.length > 1) {
          // For other types, prefer longer values (more context = better patterns)
          bestExample = field.examples.reduce((best, ex) => {
            return (ex.value && ex.value.length > best.value.length) ? ex : best;
          }, field.examples[0]);
        }
        
        exampleValue = bestExample.value;
        exampleFile = bestExample.file;
      } else if (field.example_value) {
        exampleValue = field.example_value;
        exampleFile = field.example_file;
      }
      
      if (!exampleValue || !exampleFile || !fileTexts[exampleFile]) {
        console.warn(`No example value/file for field: ${field.label}`);
        generatedSchema.push(field); // Keep field as-is
        continue;
      }
      
      const fullText = fileTexts[exampleFile];
      const position = fullText.indexOf(exampleValue);
      
      if (position === -1) {
        console.warn(`Could not find value "${exampleValue}" for field: ${field.label}`);
        generatedSchema.push(field); // Keep field as-is
        continue;
      }
      
      // Extract context before the value
      const beforeText = fullText.substring(Math.max(0, position - 750), position);
      
      // Detect field type
      const fieldType = detectDataTypeFromLabel(field.label) || detectDataType(field) || 'text';
      
      // Generate pattern hints
      const hints = generatePatternHint(beforeText, exampleValue, fieldType);
      
      // Build regex_patterns array from hints
      const regexPatterns = hints.suggestedPatterns.map(p => ({
        pattern: p.pattern,
        type: p.type
      }));
      
      // Use the first (most specific) pattern as primary
      const primaryPattern = regexPatterns.length > 0 ? regexPatterns[0].pattern : null;
      
      generatedSchema.push({
        field_id: field.field_id || field.label.toLowerCase().replace(/\s+/g, '_'),
        label: field.label,
        regex: primaryPattern,
        regex_patterns: regexPatterns,
        value_type: fieldType,
        manual_values: field.manual_values || {},
        examples: field.examples || [],
        example_value: field.example_value,
        example_file: field.example_file,
        example_context: field.example_context
      });
    }
    
    // Save schema
    await api.saveSchema(projectId, generatedSchema);
    selectedFields = generatedSchema;
    project.schema = generatedSchema;
    
    // Run extraction
    await api.runExtraction(projectId);
    await loadResults();
    
    renderExtractionTable();
    alert('Schema auto-generated and extraction completed!');
    
  } catch (error) {
    console.error('Auto-generate failed:', error);
    alert('Failed to auto-generate schema: ' + error.message);
  }
}

/**
 * Open AI Schema Builder modal
 */
async function openAISchemaBuilder() {
  try {
    if (!selectedFields || selectedFields.length === 0) {
      alert('No fields available. Please add fields with example values first.');
      return;
    }
    
    // Generate the AI prompt (same logic as before but kept for AI use)
    const prompt = await generateAIPrompt();
    
    const modal = document.getElementById('aiSchemaBuilderModal');
    document.getElementById('aiPromptText').value = prompt;
    document.getElementById('aiImportText').value = '';
    document.getElementById('aiImportPreview').style.display = 'none';
    document.getElementById('aiImportError').style.display = 'none';
    
    modal.style.display = 'flex';
    
    // Copy button handler
    document.getElementById('copyPromptBtn').onclick = () => {
      navigator.clipboard.writeText(prompt);
      const btn = document.getElementById('copyPromptBtn');
      const originalText = btn.textContent;
      btn.textContent = 'Copied!';
      setTimeout(() => { btn.textContent = originalText; }, 1500);
    };
  } catch (error) {
    alert('Failed to open AI Schema Builder: ' + error.message);
  }
}

function closeAISchemaBuilder() {
  document.getElementById('aiSchemaBuilderModal').style.display = 'none';
}

/**
 * Generate AI prompt from field examples
 */
async function generateAIPrompt() {
  const parsedFiles = project.files.filter(f => f.parsed && !f.parse_failed);
  
  if (parsedFiles.length === 0) {
    throw new Error('No parsed files available');
  }
  
  // Collect files with examples
  const filesWithExamples = new Set();
  for (const field of selectedFields) {
    if (field.examples && field.examples.length > 0) {
      field.examples.forEach(ex => {
        if (ex.file) filesWithExamples.add(ex.file);
      });
    } else if (field.example_file) {
      filesWithExamples.add(field.example_file);
    }
  }
  
  // Load text for files
  const fileTexts = {};
  for (const filename of filesWithExamples) {
    if (!filename) continue;
    try {
      const result = await api.getFileText(projectId, filename);
      fileTexts[filename] = result.text;
    } catch (e) {
      console.error(`Failed to load ${filename}:`, e);
    }
  }
  
  // Build prompt
  let prompt = `# Regex Pattern Generation Task

Generate regex patterns to extract fields from structured documents.

## OUTPUT FORMAT (JSON only, no markdown):
{
  "fields": [
    {
      "label": "Field Name",
      "value_type": "money|date|number|text",
      "regex_patterns": [
        {"pattern": "Label.*?([\\\\d,\\\\.]+)", "type": "specific"},
        {"pattern": "([\\\\d,\\\\.]+)", "type": "fallback"}
      ]
    }
  ]
}

## KEY RULES
1. Use .*? (non-greedy) to skip variable text
2. Double backslashes in JSON: \\\\s not \\s
3. Use capture groups () around the value
4. Match row labels first, then navigate to the value

## FIELDS TO EXTRACT

`;

  // Add each field with context
  selectedFields.forEach((field, idx) => {
    let exampleValue = '';
    let exampleFile = '';
    
    if (field.examples && field.examples.length > 0) {
      exampleValue = field.examples[0].value;
      exampleFile = field.examples[0].file;
    } else if (field.example_value) {
      exampleValue = field.example_value;
      exampleFile = field.example_file;
    }
    
    const fieldType = detectDataTypeFromLabel(field.label) || detectDataType(field) || 'text';
    
    prompt += `\n### Field ${idx + 1}: ${field.label}\n`;
    prompt += `Type: ${fieldType}\n`;
    prompt += `Example value: "${exampleValue}"\n`;
    
    // Add context if available
    if (exampleFile && fileTexts[exampleFile]) {
      const fullText = fileTexts[exampleFile];
      const position = fullText.indexOf(exampleValue);
      
      if (position !== -1) {
        const beforeText = fullText.substring(Math.max(0, position - 500), position);
        const afterText = fullText.substring(position + exampleValue.length, Math.min(fullText.length, position + exampleValue.length + 200));
        
        prompt += `\nContext:\n\`\`\`\n${beforeText}>>>${exampleValue}<<<${afterText}\n\`\`\`\n`;
        
        // Generate pattern hints
        const hints = generatePatternHint(beforeText, exampleValue, fieldType);
        if (hints.suggestedPatterns.length > 0) {
          prompt += `\nSuggested patterns:\n`;
          hints.suggestedPatterns.forEach((p, i) => {
            prompt += `${i + 1}. [${p.type}] \`${p.pattern}\`\n`;
          });
        }
      }
    }
    
    prompt += `\n`;
  });
  
  prompt += `\n---\nGenerate regex patterns for all fields in the JSON format above.\n`;
  
  return prompt;
}

/**
 * Validate and import AI-generated schema
 */
async function validateAndImportAI() {
  const importText = document.getElementById('aiImportText').value.trim();
  
  if (!importText) {
    showImportError('Please paste the AI-generated JSON');
    return;
  }
  
  try {
    let cleanedText = importText;
    
    // Remove markdown code blocks
    if (cleanedText.includes('```')) {
      cleanedText = cleanedText.replace(/```json\n?/g, '').replace(/```\n?/g, '').trim();
    }
    
    // Parse JSON
    let data;
    try {
      data = JSON.parse(cleanedText);
    } catch (parseError) {
      showImportError(`JSON parse error: ${parseError.message}\n\nMake sure backslashes are doubled: \\\\s not \\s`);
      return;
    }
    
    // Validate structure
    if (!data.fields || !Array.isArray(data.fields)) {
      showImportError('Invalid JSON: missing "fields" array');
      return;
    }
    
    // Validate each field
    for (const field of data.fields) {
      if (!field.label) {
        showImportError('Invalid field: missing label');
        return;
      }
      
      const hasPatterns = field.regex_patterns && Array.isArray(field.regex_patterns);
      const hasSingleRegex = field.regex;
      
      if (!hasPatterns && !hasSingleRegex) {
        showImportError(`Field "${field.label}": missing "regex" or "regex_patterns"`);
        return;
      }
      
      // Validate regex patterns
      if (hasPatterns) {
        for (const patternObj of field.regex_patterns) {
          if (!patternObj.pattern || !patternObj.type) {
            showImportError(`Field "${field.label}": invalid pattern object`);
            return;
          }
          
          try {
            new RegExp(patternObj.pattern);
          } catch (e) {
            showImportError(`Field "${field.label}": invalid regex pattern\n\n${patternObj.pattern}\n\nError: ${e.message}`);
            return;
          }
        }
      }
    }
    
    // Show preview
    const preview = document.getElementById('aiImportPreview');
    const previewContent = document.getElementById('aiImportPreviewContent');
    
    let html = '<strong style="color:#007AFF">✓ Valid JSON</strong><br><br><strong>Fields to import:</strong><ul style="margin:5px 0;padding-left:20px">';
    data.fields.forEach(f => {
      html += `<li><strong>${escapeHtml(f.label)}</strong>`;
      if (f.regex_patterns) {
        html += ` (${f.regex_patterns.length} patterns)`;
      }
      html += `</li>`;
    });
    html += '</ul>';
    
    previewContent.innerHTML = html;
    preview.style.display = 'block';
    document.getElementById('aiImportError').style.display = 'none';
    
    // Import schema
    await importAISchema(data.fields);
    
  } catch (error) {
    showImportError('Error: ' + error.message);
  }
}

/**
 * Import AI schema and run extraction
 */
async function importAISchema(fields) {
  try {
    // Convert to schema format
    const schema = fields.map(f => {
      const existingField = selectedFields.find(sf => 
        sf.field_id === f.field_id || 
        normalizeLabel(sf.label) === normalizeLabel(f.label)
      );
      
      let regexPatterns = null;
      let primaryRegex = null;
      
      if (f.regex_patterns && Array.isArray(f.regex_patterns)) {
        regexPatterns = f.regex_patterns;
        primaryRegex = f.regex_patterns[0].pattern;
      } else if (f.regex) {
        primaryRegex = f.regex;
      }
      
      return {
        field_id: f.field_id || f.label.toLowerCase().replace(/\s+/g, '_'),
        label: f.label,
        regex: primaryRegex,
        regex_patterns: regexPatterns,
        value_type: f.value_type || 'text',
        manual_values: existingField?.manual_values || {},
        examples: existingField?.examples || [],
        example_value: existingField?.example_value,
        example_file: existingField?.example_file,
        example_context: existingField?.example_context
      };
    });
    
    // Save and extract
    document.getElementById('validateImportBtn').textContent = 'Running extraction...';
    document.getElementById('validateImportBtn').disabled = true;
    
    await api.saveSchema(projectId, schema);
    selectedFields = schema;
    project.schema = schema;
    
    await api.runExtraction(projectId);
    await loadResults();
    
    closeAISchemaBuilder();
    renderExtractionTable();
    
    alert('Schema imported and extraction completed!');
    
  } catch (error) {
    showImportError('Import failed: ' + error.message);
  } finally {
    document.getElementById('validateImportBtn').textContent = 'Validate & Import';
    document.getElementById('validateImportBtn').disabled = false;
  }
}

function showImportError(message) {
  const errorDiv = document.getElementById('aiImportError');
  errorDiv.textContent = message;
  errorDiv.style.display = 'block';
}


async function runExtraction() {
  try {
    const btn = document.getElementById('runExtractionBtn');
    btn.textContent = 'Extracting...';
    btn.disabled = true;
    
    await api.runExtraction(projectId);
    await loadResults();
    
    alert('Extraction completed!');
  } catch (error) {
    alert('Extraction failed: ' + error.message);
  } finally {
    const btn = document.getElementById('runExtractionBtn');
    btn.textContent = 'Run Extraction';
    btn.disabled = false;
  }
}

async function loadResults() {
  try {
    extractionResults = await api.getResults(projectId);
    project.last_extracted = extractionResults.extracted_at;
    renderExtractionTable();
  } catch (error) {
    console.error('Failed to load results:', error);
  }
}

async function handleFileUpload(files) {
  const progressList = document.getElementById('uploadProgressList');
  const uploadZone = document.getElementById('uploadZone');
  
  // Hide upload zone, show progress list
  uploadZone.style.display = 'none';
  progressList.style.display = 'block';
  
  // Create progress items for each file
  progressList.innerHTML = files.map((file, idx) => `
    <div class="upload-progress-item" id="progress-${idx}" data-status="pending">
      <div class="file-icon">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
          <polyline points="14 2 14 8 20 8"></polyline>
        </svg>
      </div>
      <div class="file-info">
        <div class="file-name">${escapeHtml(file.name)}</div>
        <div class="file-status-text">Waiting...</div>
        <div class="progress-bar">
          <div class="progress-bar-fill" style="width: 0%"></div>
        </div>
      </div>
      <div class="status-icon pending">○</div>
    </div>
  `).join('');
  
  // Process files one by one
  const results = { success: [], failed: [], skipped: 0 };
  
  for (let i = 0; i < files.length; i++) {
    const file = files[i];
    const progressItem = document.getElementById(`progress-${i}`);
    const statusText = progressItem.querySelector('.file-status-text');
    const progressBar = progressItem.querySelector('.progress-bar-fill');
    const statusIcon = progressItem.querySelector('.status-icon');
    
    // Mark as processing
    progressItem.classList.add('processing');
    statusText.textContent = 'Uploading...';
    progressBar.style.width = '30%';
    statusIcon.innerHTML = '⟳';
    statusIcon.className = 'status-icon pending';
    
    try {
      // Upload single file
      const result = await api.uploadFiles(projectId, [file]);
      
      // Update progress
      statusText.textContent = 'Parsing with OCR...';
      progressBar.style.width = '70%';
      
      // Small delay to show parsing state
      await new Promise(resolve => setTimeout(resolve, 300));
      
      if (result.success && result.success.length > 0) {
        // Success
        progressItem.classList.remove('processing');
        progressItem.classList.add('completed');
        statusText.textContent = 'Parsed successfully';
        progressBar.style.width = '100%';
        statusIcon.innerHTML = '✓';
        statusIcon.className = 'status-icon success';
        results.success.push(...result.success);
      } else if (result.skipped > 0) {
        // Already exists
        progressItem.classList.remove('processing');
        progressItem.classList.add('completed');
        statusText.textContent = 'Already in project';
        progressBar.style.width = '100%';
        statusIcon.innerHTML = '○';
        statusIcon.className = 'status-icon pending';
        results.skipped++;
      } else if (result.failed && result.failed.length > 0) {
        // Failed
        progressItem.classList.remove('processing');
        progressItem.classList.add('failed');
        statusText.textContent = result.failed[0].error || 'Failed to parse';
        progressBar.style.width = '100%';
        statusIcon.innerHTML = '✗';
        statusIcon.className = 'status-icon error';
        results.failed.push(...result.failed);
      }
    } catch (error) {
      // Error
      progressItem.classList.remove('processing');
      progressItem.classList.add('failed');
      statusText.textContent = error.message;
      progressBar.style.width = '100%';
      statusIcon.innerHTML = '✗';
      statusIcon.className = 'status-icon error';
      results.failed.push({ filename: file.name, error: error.message });
    }
  }
  
  // Reload project data
  await loadProject();
  
  // Auto-open first successfully uploaded file
  if (results.success.length > 0) {
    await selectFile(results.success[0].filename);
  }
  
  // Auto-run extraction if we have fields defined and new files were parsed
  if (results.success.length > 0 && selectedFields.length > 0) {
    // Show extraction status
    const extractionItem = document.createElement('div');
    extractionItem.className = 'upload-progress-item processing';
    extractionItem.innerHTML = `
      <div class="file-icon">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline>
        </svg>
      </div>
      <div class="file-info">
        <div class="file-name">Running extraction...</div>
        <div class="file-status-text">Processing ${results.success.length} new file(s)</div>
        <div class="progress-bar">
          <div class="progress-bar-fill" style="width: 50%"></div>
        </div>
      </div>
      <div class="status-icon pending">⟳</div>
    `;
    progressList.appendChild(extractionItem);
    
    try {
      await runExtraction();
      extractionItem.classList.remove('processing');
      extractionItem.classList.add('completed');
      extractionItem.querySelector('.file-status-text').textContent = 'Extraction complete';
      extractionItem.querySelector('.progress-bar-fill').style.width = '100%';
      extractionItem.querySelector('.status-icon').innerHTML = '✓';
      extractionItem.querySelector('.status-icon').className = 'status-icon success';
    } catch (error) {
      extractionItem.classList.remove('processing');
      extractionItem.classList.add('failed');
      extractionItem.querySelector('.file-status-text').textContent = 'Extraction failed: ' + error.message;
      extractionItem.querySelector('.progress-bar-fill').style.width = '100%';
      extractionItem.querySelector('.status-icon').innerHTML = '✗';
      extractionItem.querySelector('.status-icon').className = 'status-icon error';
    }
  }
  
  // Close modal after 2 seconds
  setTimeout(() => {
    closeUploadModal();
  }, 2000);
}

function openUploadModal() {
  const modal = document.getElementById('uploadModal');
  const uploadZone = document.getElementById('uploadZone');
  const progressList = document.getElementById('uploadProgressList');
  
  // Reset modal state
  uploadZone.style.display = 'block';
  progressList.style.display = 'none';
  progressList.innerHTML = '';
  
  modal.style.display = 'flex';
}

function closeUploadModal() {
  const modal = document.getElementById('uploadModal');
  const uploadZone = document.getElementById('uploadZone');
  const progressList = document.getElementById('uploadProgressList');
  
  modal.style.display = 'none';
  
  // Reset state
  uploadZone.style.display = 'block';
  progressList.style.display = 'none';
  progressList.innerHTML = '';
  document.getElementById('fileInput').value = '';
}

function createFileItemHTML(filename) {
  return `
    <div class="file-item" onclick="selectFile('${escapeHtml(filename)}')">
      <span class="file-name">${escapeHtml(filename)}</span>
      <span class="file-status">✓ Parsed</span>
    </div>
  `;
}

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

async function navigateToValue(filename, fieldId, value) {
  if (!value || value === '—') return;
  
  // Handle multiple values (separated by " | ")
  const values = value.split(' | ').map(v => v.trim());
  const primaryValue = values[0]; // Use first value for navigation
  
  try {
    // Load the file if not already loaded
    if (currentFile !== filename) {
      await selectFile(filename);
    }
    
    // Find the field to get example position
    const field = selectedFields.find(f => f.field_id === fieldId);
    let targetPosition = null;
    
    // Check if we have an example position for this file
    if (field) {
      const examples = field.examples || [];
      for (const ex of examples) {
        if (ex.file === filename && ex.position !== null) {
          targetPosition = ex.position;
          break;
        }
      }
    }
    
    // Find and highlight the value in the document
    const preview = document.getElementById('documentPreview');
    const text = preview.textContent;
    
    // Remove previous highlights
    preview.innerHTML = '';
    
    // Find all occurrences of the primary value
    const regex = new RegExp(escapeRegex(primaryValue), 'gi');
    let lastIndex = 0;
    let match;
    let allMatches = [];
    
    while ((match = regex.exec(text)) !== null) {
      allMatches.push({
        index: match.index,
        length: match[0].length,
        text: match[0]
      });
    }
    
    // Determine which match to highlight as "current"
    let currentMatchIndex = 0;
    if (targetPosition !== null && allMatches.length > 1) {
      // Find the match closest to the example position
      let closestDistance = Infinity;
      allMatches.forEach((m, idx) => {
        const distance = Math.abs(m.index - targetPosition);
        if (distance < closestDistance) {
          closestDistance = distance;
          currentMatchIndex = idx;
        }
      });
    }
    
    // Rebuild the preview with highlights
    lastIndex = 0;
    let firstMatchElement = null;
    
    allMatches.forEach((m, idx) => {
      // Add text before match
      const beforeText = document.createTextNode(text.substring(lastIndex, m.index));
      preview.appendChild(beforeText);
      
      // Add highlighted match
      const highlight = document.createElement('span');
      highlight.className = idx === currentMatchIndex ? 'highlight-current' : 'highlight';
      highlight.textContent = m.text;
      preview.appendChild(highlight);
      
      if (idx === currentMatchIndex) {
        firstMatchElement = highlight;
      }
      
      lastIndex = m.index + m.length;
    });
    
    // Add remaining text
    if (lastIndex < text.length) {
      const remainingText = document.createTextNode(text.substring(lastIndex));
      preview.appendChild(remainingText);
    }
    
    // Scroll to the current match (closest to example position)
    if (firstMatchElement) {
      firstMatchElement.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  } catch (error) {
    console.error('Navigation failed:', error);
  }
}

function escapeRegex(str) {
  return str.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

/**
 * Check if any modal is currently open
 * @returns {boolean} true if a modal is open
 */
function isModalOpen() {
  const modals = document.querySelectorAll('.modal');
  for (const modal of modals) {
    if (modal.style.display === 'flex' || modal.style.display === 'block') {
      return true;
    }
  }
  return false;
}

function showFieldRegex(fieldIndex) {
  const field = selectedFields[fieldIndex];
  
  let message = `Field: ${field.label}\n\n`;
  
  if (field.regex) {
    message += `Regex Pattern:\n${field.regex}\n\n`;
    message += `Value Type: ${field.value_type || 'text'}`;
  } else {
    message += 'No regex pattern set yet.\n\n';
    if (field.example_value) {
      message += `Example value: "${field.example_value}"\n`;
      message += `From file: ${field.example_file || 'N/A'}\n\n`;
    }
    message += 'Use "Export for AI" to generate regex patterns for all fields.';
  }
  
  alert(message);
}

function exportToTSV() {
  if (!extractionResults || !extractionResults.results || selectedFields.length === 0) {
    alert('No extraction results to export');
    return;
  }
  
  const parsedFiles = project.files.filter(f => f.parsed && !f.parse_failed);
  
  // Build TSV header
  let tsv = 'File\t' + selectedFields.map(f => f.label).join('\t') + '\n';
  
  // Build TSV rows
  parsedFiles.forEach(file => {
    let row = file.filename;
    
    selectedFields.forEach(field => {
      const value = getCellValue(file.filename, field);
      // Escape tabs and newlines in values
      const cleanValue = value ? value.replace(/\t/g, ' ').replace(/\n/g, ' ') : '';
      row += '\t' + cleanValue;
    });
    
    tsv += row + '\n';
  });
  
  // Copy to clipboard
  navigator.clipboard.writeText(tsv).then(() => {
    alert('TSV data copied to clipboard! You can paste it into Excel or Google Sheets.');
  }).catch(err => {
    alert('Failed to copy to clipboard: ' + err.message);
  });
}

