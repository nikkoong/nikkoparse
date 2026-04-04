/**
 * Home Page JavaScript
 */

let projects = [];
let projectToDelete = null;

// Load projects on page load
document.addEventListener('DOMContentLoaded', () => {
  loadProjects();
  
  // Modal handlers
  document.getElementById('cancelBtn').addEventListener('click', hideNewProjectModal);
  document.getElementById('createBtn').addEventListener('click', createProject);
  document.getElementById('deleteCancelBtn').addEventListener('click', hideDeleteModal);
  document.getElementById('deleteConfirmBtn').addEventListener('click', confirmDelete);
  
  // Enter key in project name input
  document.getElementById('projectNameInput').addEventListener('keypress', (e) => {
    if (e.key === 'Enter') createProject();
  });
});

async function loadProjects() {
  try {
    projects = await api.getProjects();
    renderProjects();
  } catch (error) {
    showError('Failed to load projects');
  }
}

function renderProjects() {
  const list = document.getElementById('projectsList');
  
  // Always start with the New Project card
  let html = `
    <div class="project-card new-project-card" onclick="showNewProjectModal()">
      <div class="new-project-content">
        <span class="new-project-icon">+</span>
        <span class="new-project-text">New Project</span>
      </div>
    </div>
  `;
  
  // Add existing projects
  html += projects.map(project => `
    <div class="project-card" onclick="openProject('${project.id}')">
      <div class="project-info">
        <h3>${escapeHtml(project.name)}</h3>
        <p>${project.doc_count} documents • Created ${formatDate(project.created_at)}</p>
      </div>
      <button class="btn-delete" onclick="event.stopPropagation(); deleteProject('${project.id}', '${escapeHtml(project.name)}')">
        Delete
      </button>
    </div>
  `).join('');
  
  list.innerHTML = html;
}

function showNewProjectModal() {
  document.getElementById('newProjectModal').classList.remove('hidden');
  document.getElementById('projectNameInput').value = '';
  document.getElementById('projectNameInput').focus();
}

function hideNewProjectModal() {
  document.getElementById('newProjectModal').classList.add('hidden');
}

async function createProject() {
  const name = document.getElementById('projectNameInput').value.trim();
  
  if (!name) {
    alert('Please enter a project name');
    return;
  }
  
  try {
    await api.createProject(name);
    hideNewProjectModal();
    await loadProjects();
  } catch (error) {
    showError('Failed to create project');
  }
}

function deleteProject(projectId, projectName) {
  projectToDelete = { id: projectId, name: projectName };
  document.getElementById('deleteModal').classList.remove('hidden');
}

function hideDeleteModal() {
  document.getElementById('deleteModal').classList.add('hidden');
  projectToDelete = null;
}

async function confirmDelete() {
  if (!projectToDelete) return;
  
  try {
    await api.deleteProject(projectToDelete.id);
    hideDeleteModal();
    await loadProjects();
  } catch (error) {
    showError('Failed to delete project');
  }
}

function openProject(projectId) {
  window.location.href = `/project/${projectId}`;
}

function formatDate(isoString) {
  const date = new Date(isoString);
  return date.toLocaleDateString();
}

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

function showError(message) {
  alert(message);  // Simple for now, can enhance later
}
