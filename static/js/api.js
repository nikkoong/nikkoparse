/**
 * API Client
 * Handles all HTTP requests to the backend
 */

const api = {
  // Projects
  async getProjects() {
    const response = await fetch('/api/projects');
    return await response.json();
  },

  async createProject(name) {
    const response = await fetch('/api/projects', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name })
    });
    return await response.json();
  },

  async getProject(id) {
    const response = await fetch(`/api/projects/${id}`);
    return await response.json();
  },

  async deleteProject(id) {
    const response = await fetch(`/api/projects/${id}`, {
      method: 'DELETE'
    });
    return await response.json();
  },

  async renameProject(id, newName) {
    const response = await fetch(`/api/projects/${id}/rename`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: newName })
    });
    return await response.json();
  },

  // Files
  async uploadFiles(projectId, files) {
    const formData = new FormData();
    for (const file of files) {
      formData.append('files', file);
    }
    
    const response = await fetch(`/api/projects/${projectId}/files`, {
      method: 'POST',
      body: formData
    });
    
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || `Upload failed with status ${response.status}`);
    }
    
    return await response.json();
  },

  async getFileText(projectId, filename) {
    const response = await fetch(`/api/projects/${projectId}/files/${encodeURIComponent(filename)}/text`);
    return await response.json();
  },

  // Schema
  async getSuggestions(projectId) {
    const response = await fetch(`/api/projects/${projectId}/suggestions`);
    return await response.json();
  },

  async saveSchema(projectId, schema) {
    const response = await fetch(`/api/projects/${projectId}/schema`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ schema })
    });
    return await response.json();
  },

  async generateRegex(projectId, highlightedValue, contextLines) {
    const response = await fetch(`/api/projects/${projectId}/schema/generate-regex`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ 
        highlighted_value: highlightedValue,
        context_lines: contextLines
      })
    });
    return await response.json();
  },

  // Extraction
  async runExtraction(projectId) {
    const response = await fetch(`/api/projects/${projectId}/extract`, {
      method: 'POST'
    });
    return await response.json();
  },

  // Results
  async getResults(projectId) {
    const response = await fetch(`/api/projects/${projectId}/results`);
    return await response.json();
  },

  async saveOverride(projectId, filename, fieldId, overrideValue) {
    const response = await fetch(`/api/projects/${projectId}/results/${encodeURIComponent(filename)}/${fieldId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ override_value: overrideValue })
    });
    return await response.json();
  },

  async clearOverride(projectId, filename, fieldId) {
    const response = await fetch(`/api/projects/${projectId}/results/${encodeURIComponent(filename)}/${fieldId}`, {
      method: 'DELETE'
    });
    return await response.json();
  },

  // Regex Preview
  async previewRegex(regex, text) {
    const response = await fetch('/api/regex-preview', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ regex, text })
    });
    return await response.json();
  },

  // AI Schema Export/Import
  async exportForAI(projectId) {
    const response = await fetch(`/api/projects/${projectId}/export-for-ai`);
    return await response.json();
  },

  async importAISchema(projectId, schema, merge = false) {
    const response = await fetch(`/api/projects/${projectId}/import-ai-schema`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ schema, merge })
    });
    return await response.json();
  }
};
