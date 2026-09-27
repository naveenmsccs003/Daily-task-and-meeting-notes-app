// Light/dark theme toggle. The early inline script in base.html <head>
// already applied the saved theme before paint (no flash); this file just
// wires up the sidebar toggle button and keeps localStorage in sync.
(function () {
    var STORAGE_KEY = 'dtmt_theme';

    function currentTheme() {
        return document.documentElement.getAttribute('data-bs-theme') || 'light';
    }

    function applyIcon(theme) {
        var icon = document.getElementById('themeToggleIcon');
        var label = document.getElementById('themeToggleLabel');
        if (icon) {
            icon.className = theme === 'dark' ? 'bi bi-sun' : 'bi bi-moon-stars';
        }
        if (label) {
            label.textContent = theme === 'dark' ? 'Light Mode' : 'Dark Mode';
        }
    }

    document.addEventListener('DOMContentLoaded', function () {
        applyIcon(currentTheme());

        var btn = document.getElementById('themeToggleBtn');
        if (!btn) return;

        btn.addEventListener('click', function () {
            var next = currentTheme() === 'dark' ? 'light' : 'dark';
            document.documentElement.setAttribute('data-bs-theme', next);
            try { localStorage.setItem(STORAGE_KEY, next); } catch (e) { /* private mode: ignore */ }
            applyIcon(next);
        });
    });
})();
