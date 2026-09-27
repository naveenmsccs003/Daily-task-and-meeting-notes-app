// Shared behavior: CSRF helper, sidebar toggle, delete confirmation,
// and the custom-date-range toggle used by dashboard/tasks/meetings/reports.

function getCsrfToken() {
    const meta = document.querySelector('meta[name="csrf-token"]');
    return meta ? meta.getAttribute('content') : '';
}

document.addEventListener('DOMContentLoaded', function () {
    // Mobile sidebar toggle
    const toggleBtn = document.getElementById('sidebarToggle');
    const sidebar = document.getElementById('sidebar');
    if (toggleBtn && sidebar) {
        toggleBtn.addEventListener('click', function () {
            sidebar.classList.toggle('open');
        });
    }

    // Confirm before any destructive delete form submits
    document.querySelectorAll('.delete-form').forEach(function (form) {
        form.addEventListener('submit', function (e) {
            if (!confirm('Are you sure you want to delete this item? This cannot be undone.')) {
                e.preventDefault();
            }
        });
    });

    // Period select -> show/hide custom date range fields, auto-submit otherwise
    const periodSelect = document.getElementById('periodSelect');
    if (periodSelect) {
        periodSelect.addEventListener('change', function () {
            const form = periodSelect.closest('form');
            const customFields = form.querySelectorAll('.custom-range-field');
            if (periodSelect.value === 'custom') {
                customFields.forEach(function (f) { f.hidden = false; });
            } else {
                customFields.forEach(function (f) { f.hidden = true; });
                form.submit();
            }
        });
    }
});
