/**
 * Student Management CRUD Application
 * Clean Vanilla JavaScript communicating with Flask REST API & MongoDB
 */

document.addEventListener('DOMContentLoaded', () => {
  // State
  let allStudents = [];
  let studentToDelete = null;
  const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || '';

  // DOM Elements
  const tableContainer = document.getElementById('tableContainer');
  const studentsTable = document.getElementById('studentsTable');
  const studentsTableBody = document.getElementById('studentsTableBody');
  const loadingState = document.getElementById('loadingState');
  const emptyState = document.getElementById('emptyState');
  const emptyTitle = document.getElementById('emptyTitle');
  const emptyDescription = document.getElementById('emptyDescription');
  const emptyAddBtn = document.getElementById('emptyAddBtn');

  // Stats
  const statTotalStudents = document.getElementById('statTotalStudents');
  const statTotalCourses = document.getElementById('statTotalCourses');

  // Filters & Search
  const searchInput = document.getElementById('searchInput');
  const clearSearchBtn = document.getElementById('clearSearchBtn');
  const courseFilter = document.getElementById('courseFilter');
  const yearFilter = document.getElementById('yearFilter');
  const refreshBtn = document.getElementById('refreshBtn');

  // Modals & Forms
  const openAddModalBtn = document.getElementById('openAddModalBtn');
  const studentDialog = document.getElementById('studentDialog');
  const closeDialogBtn = document.getElementById('closeDialogBtn');
  const cancelDialogBtn = document.getElementById('cancelDialogBtn');
  const studentForm = document.getElementById('studentForm');
  const dialogTitle = document.getElementById('dialogTitle');
  const dialogSubtitle = document.getElementById('dialogSubtitle');
  const saveBtnText = document.getElementById('saveBtnText');
  const saveBtnSpinner = document.getElementById('saveBtnSpinner');
  const saveStudentBtn = document.getElementById('saveStudentBtn');

  // Delete Dialog
  const deleteDialog = document.getElementById('deleteDialog');
  const deleteStudentName = document.getElementById('deleteStudentName');
  const confirmDeleteBtn = document.getElementById('confirmDeleteBtn');
  const cancelDeleteBtn = document.getElementById('cancelDeleteBtn');
  const deleteBtnSpinner = document.getElementById('deleteBtnSpinner');

  // Form Fields & Errors
  const studentIdInput = document.getElementById('studentId');
  const studentNameInput = document.getElementById('studentName');
  const studentEmailInput = document.getElementById('studentEmail');
  const studentCourseInput = document.getElementById('studentCourse');
  const studentYearInput = document.getElementById('studentYear');

  const nameError = document.getElementById('nameError');
  const emailError = document.getElementById('emailError');
  const courseError = document.getElementById('courseError');
  const yearError = document.getElementById('yearError');

  // Toast Container
  const toastContainer = document.getElementById('toastContainer');

  // --- INITIALIZATION ---
  fetchStudents();

  // --- EVENT LISTENERS ---
  openAddModalBtn.addEventListener('click', openAddModal);
  emptyAddBtn.addEventListener('click', openAddModal);
  closeDialogBtn.addEventListener('click', () => studentDialog.close());
  cancelDialogBtn.addEventListener('click', () => studentDialog.close());

  // Close modals on clicking backdrop (native <dialog> feature)
  studentDialog.addEventListener('click', (e) => {
    if (e.target === studentDialog) studentDialog.close();
  });
  deleteDialog.addEventListener('click', (e) => {
    if (e.target === deleteDialog) deleteDialog.close();
  });

  cancelDeleteBtn.addEventListener('click', () => deleteDialog.close());
  confirmDeleteBtn.addEventListener('click', handleDeleteConfirm);

  studentForm.addEventListener('submit', handleFormSubmit);

  searchInput.addEventListener('input', () => {
    if (searchInput.value.trim().length > 0) {
      clearSearchBtn.hidden = false;
    } else {
      clearSearchBtn.hidden = true;
    }
    renderStudents();
  });

  clearSearchBtn.addEventListener('click', () => {
    searchInput.value = '';
    clearSearchBtn.hidden = true;
    searchInput.focus();
    renderStudents();
  });

  courseFilter.addEventListener('change', renderStudents);
  yearFilter.addEventListener('change', renderStudents);
  refreshBtn.addEventListener('click', () => {
    showToast('Refreshing student records...', 'info');
    fetchStudents();
  });

  // Table Event Delegation for Edit & Delete buttons
  studentsTableBody.addEventListener('click', (e) => {
    const editBtn = e.target.closest('.btn-action-edit');
    if (editBtn) {
      const studentId = editBtn.dataset.id;
      openEditModal(studentId);
      return;
    }

    const deleteBtn = e.target.closest('.btn-action-delete');
    if (deleteBtn) {
      const studentId = deleteBtn.dataset.id;
      const studentName = deleteBtn.dataset.name;
      openDeleteModal(studentId, studentName);
      return;
    }
  });

  // --- CORE FUNCTIONS ---

  /**
   * Set view states mutually exclusively:
   * - 'loading': only loading spinner/indicator is visible
   * - 'empty': only empty state is visible
   * - 'populated': only table with rows is visible
   * @param {'loading' | 'empty' | 'populated'} state
   */
  function setViewState(state) {
    if (state === 'loading') {
      loadingState.hidden = false;
      emptyState.hidden = true;
      if (tableContainer) tableContainer.hidden = true;
      studentsTable.hidden = true;
    } else if (state === 'empty') {
      loadingState.hidden = true;
      emptyState.hidden = false;
      if (tableContainer) tableContainer.hidden = true;
      studentsTable.hidden = true;
    } else if (state === 'populated') {
      loadingState.hidden = true;
      emptyState.hidden = true;
      if (tableContainer) tableContainer.hidden = false;
      studentsTable.hidden = false;
    }
  }

  /**
   * Fetch all students from the Flask backend (GET /students)
   */
  async function fetchStudents() {
    setViewState('loading');

    try {
      const response = await fetch('/students', {
        headers: {
          'Accept': 'application/json'
        }
      });

      if (response.status === 401) {
        window.location.href = '/login?next=' + encodeURIComponent(window.location.pathname);
        return;
      }

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.error || `HTTP error ${response.status}`);
      }

      allStudents = await response.json();
      updateStats();
      populateCourseFilter();
      renderStudents();
    } catch (error) {
      console.error('Fetch error:', error);
      showToast(`Error loading students: ${error.message}`, 'error');
      // If error occurs, render empty state with error message
      emptyTitle.textContent = 'Connection Error';
      emptyDescription.textContent = 'Could not load student data from MongoDB. Please make sure Flask and MongoDB are running.';
      emptyAddBtn.hidden = true;
      setViewState('empty');
    }
  }

  /**
   * Filter and render students into the table view
   */
  function renderStudents() {
    const searchQuery = searchInput.value.trim().toLowerCase();
    const selectedCourse = courseFilter.value.trim().toLowerCase();
    const selectedYear = yearFilter.value.trim();

    const filtered = allStudents.filter(student => {
      const name = (student.name || '').toLowerCase();
      const email = (student.email || '').toLowerCase();
      const course = (student.course || '').toLowerCase();
      const year = String(student.year || '').trim();

      const matchesSearch = !searchQuery || 
        name.includes(searchQuery) || 
        email.includes(searchQuery) || 
        course.includes(searchQuery);

      const matchesCourse = !selectedCourse || course === selectedCourse;
      const matchesYear = !selectedYear || year === selectedYear;

      return matchesSearch && matchesCourse && matchesYear;
    });

    if (filtered.length === 0) {
      if (allStudents.length === 0) {
        emptyTitle.textContent = 'No Students Found';
        emptyDescription.textContent = 'There are currently no student records in the MongoDB database.';
        emptyAddBtn.hidden = false;
      } else {
        emptyTitle.textContent = 'No Matching Results';
        emptyDescription.textContent = 'No students match your search or filter criteria. Try adjusting your search query.';
        emptyAddBtn.hidden = true;
      }
      setViewState('empty');
      return;
    }

    // Render table rows
    studentsTableBody.innerHTML = '';

    filtered.forEach(student => {
      const row = document.createElement('tr');
      const initials = getInitials(student.name);

      row.innerHTML = `
        <td>
          <div class="student-profile">
            <div class="avatar-circle">${escapeHtml(initials)}</div>
            <div class="student-meta">
              <span class="student-name">${escapeHtml(student.name)}</span>
              <span class="student-id-sub">ID: ${escapeHtml(student.id.slice(-6))}</span>
            </div>
          </div>
        </td>
        <td>
          <a href="mailto:${escapeHtml(student.email)}" class="student-email">${escapeHtml(student.email)}</a>
        </td>
        <td>
          <span class="badge badge-course">${escapeHtml(student.course)}</span>
        </td>
        <td>
          <span class="badge badge-year">Year ${escapeHtml(String(student.year))}</span>
        </td>
        <td class="text-right">
          <div class="action-buttons">
            <button class="btn-action btn-action-edit" data-id="${student.id}" title="Edit Student" aria-label="Edit Student">
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path>
                <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path>
              </svg>
            </button>
            <button class="btn-action btn-action-delete" data-id="${student.id}" data-name="${escapeHtml(student.name)}" title="Delete Student" aria-label="Delete Student">
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <polyline points="3 6 5 6 21 6"></polyline>
                <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
              </svg>
            </button>
          </div>
        </td>
      `;
      studentsTableBody.appendChild(row);
    });

    setViewState('populated');
  }

  /**
   * Handle Create / Update Form Submit
   */
  async function handleFormSubmit(e) {
    e.preventDefault();

    clearFieldErrors();

    const name = studentNameInput.value.trim();
    const email = studentEmailInput.value.trim().toLowerCase();
    const course = studentCourseInput.value.trim();
    const year = studentYearInput.value.trim();
    const studentId = studentIdInput.value.trim();

    // Client-side Validation
    let hasError = false;

    if (!name) {
      showFieldError(studentNameInput, nameError, 'Full name is required.');
      hasError = true;
    } else if (name.length < 2) {
      showFieldError(studentNameInput, nameError, 'Name must be at least 2 characters.');
      hasError = true;
    }

    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!email) {
      showFieldError(studentEmailInput, emailError, 'Email address is required.');
      hasError = true;
    } else if (!emailRegex.test(email)) {
      showFieldError(studentEmailInput, emailError, 'Please enter a valid email address.');
      hasError = true;
    }

    if (!course) {
      showFieldError(studentCourseInput, courseError, 'Course is required.');
      hasError = true;
    }

    const parsedYear = parseInt(year, 10);
    if (!year || isNaN(parsedYear) || parsedYear < 1 || parsedYear > 8) {
      showFieldError(studentYearInput, yearError, 'Year must be a number between 1 and 8.');
      hasError = true;
    }

    if (hasError) return;

    const studentData = {
      name: name,
      email: email,
      course: course,
      year: parsedYear
    };

    // Toggle button loading state
    saveStudentBtn.disabled = true;
    saveBtnSpinner.hidden = false;

    try {
      const isEdit = Boolean(studentId);
      const url = isEdit ? `/students/${encodeURIComponent(studentId)}` : '/students';
      const method = isEdit ? 'PUT' : 'POST';

      const response = await fetch(url, {
        method: method,
        headers: {
          'Content-Type': 'application/json',
          'X-CSRF-Token': csrfToken
        },
        body: JSON.stringify(studentData)
      });

      if (response.status === 401) {
        window.location.href = '/login?next=' + encodeURIComponent(window.location.pathname);
        return;
      }

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || 'Server request failed');
      }

      showToast(isEdit ? 'Student updated successfully!' : 'Student added successfully!', 'success');
      studentDialog.close();
      await fetchStudents();
    } catch (error) {
      console.error('Save error:', error);
      showToast(error.message, 'error');
    } finally {
      saveStudentBtn.disabled = false;
      saveBtnSpinner.hidden = true;
    }
  }

  /**
   * Handle Delete Confirmation
   */
  async function handleDeleteConfirm() {
    if (!studentToDelete) return;

    confirmDeleteBtn.disabled = true;
    deleteBtnSpinner.hidden = false;

    try {
      const response = await fetch(`/students/${encodeURIComponent(studentToDelete.id)}`, {
        method: 'DELETE',
        headers: {
          'X-CSRF-Token': csrfToken
        }
      });

      if (response.status === 401) {
        window.location.href = '/login?next=' + encodeURIComponent(window.location.pathname);
        return;
      }

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || 'Failed to delete student');
      }

      showToast('Student deleted successfully!', 'success');
      deleteDialog.close();
      studentToDelete = null;
      await fetchStudents();
    } catch (error) {
      console.error('Delete error:', error);
      showToast(error.message, 'error');
    } finally {
      confirmDeleteBtn.disabled = false;
      deleteBtnSpinner.hidden = true;
    }
  }

  /**
   * Modal Open Helpers
   */
  function openAddModal() {
    studentForm.reset();
    studentIdInput.value = '';
    clearFieldErrors();
    dialogTitle.textContent = 'Add New Student';
    dialogSubtitle.textContent = "Enter the student's academic and contact details.";
    saveBtnText.textContent = 'Save Student';
    studentDialog.showModal();
    studentNameInput.focus();
  }

  function openEditModal(studentId) {
    const student = allStudents.find(s => s.id === studentId);
    if (!student) {
      showToast('Student details not found', 'error');
      return;
    }

    studentForm.reset();
    clearFieldErrors();

    studentIdInput.value = student.id;
    studentNameInput.value = student.name || '';
    studentEmailInput.value = student.email || '';
    studentCourseInput.value = student.course || '';
    studentYearInput.value = student.year || '';

    dialogTitle.textContent = 'Edit Student Details';
    dialogSubtitle.textContent = `Updating information for ${student.name}.`;
    saveBtnText.textContent = 'Update Student';
    studentDialog.showModal();
    studentNameInput.focus();
  }

  function openDeleteModal(studentId, studentName) {
    studentToDelete = { id: studentId, name: studentName };
    deleteStudentName.textContent = studentName || 'this student';
    deleteDialog.showModal();
  }

  // --- STATS & FILTER HELPERS ---

  function updateStats() {
    statTotalStudents.textContent = allStudents.length;

    const uniqueCourses = new Set(
      allStudents
        .map(s => (s.course || '').trim())
        .filter(c => c.length > 0)
    );
    statTotalCourses.textContent = uniqueCourses.size;
  }

  function populateCourseFilter() {
    const currentSelected = courseFilter.value;
    const courses = Array.from(
      new Set(
        allStudents
          .map(s => (s.course || '').trim())
          .filter(c => c.length > 0)
      )
    ).sort();

    // Preserve 'All Courses' option
    courseFilter.innerHTML = '<option value="">All Courses</option>';
    courses.forEach(c => {
      const option = document.createElement('option');
      option.value = c;
      option.textContent = c;
      if (c.toLowerCase() === currentSelected.toLowerCase()) {
        option.selected = true;
      }
      courseFilter.appendChild(option);
    });
  }

  // --- VALIDATION & TOAST UTILITIES ---

  function showFieldError(input, errorElement, message) {
    input.classList.add('input-error');
    errorElement.textContent = message;
  }

  function clearFieldErrors() {
    [studentNameInput, studentEmailInput, studentCourseInput, studentYearInput].forEach(inp => {
      inp.classList.remove('input-error');
    });
    [nameError, emailError, courseError, yearError].forEach(err => {
      err.textContent = '';
    });
  }

  function showToast(message, type = 'success') {
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;

    let iconSvg = '';
    if (type === 'success') {
      iconSvg = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#10b981" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>`;
    } else if (type === 'error') {
      iconSvg = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#ef4444" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line></svg>`;
    } else {
      iconSvg = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#3b82f6" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="16" x2="12" y2="12"></line><line x1="12" y1="8" x2="12.01" y2="8"></line></svg>`;
    }

    toast.innerHTML = `
      <div class="toast-message">
        ${iconSvg}
        <span>${escapeHtml(message)}</span>
      </div>
      <button type="button" class="toast-close" aria-label="Close notification">&times;</button>
    `;

    toast.querySelector('.toast-close').addEventListener('click', () => {
      dismissToast(toast);
    });

    toastContainer.appendChild(toast);

    setTimeout(() => {
      dismissToast(toast);
    }, 4000);
  }

  function dismissToast(toast) {
    if (!toast || toast.classList.contains('toast-fade-out')) return;
    toast.classList.add('toast-fade-out');
    setTimeout(() => {
      toast.remove();
    }, 300);
  }

  function getInitials(name) {
    if (!name) return '?';
    const parts = name.trim().split(/\s+/);
    if (parts.length === 1) return parts[0].substring(0, 2).toUpperCase();
    return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
  }

  function escapeHtml(str) {
    if (str === null || str === undefined) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }
});
