document.addEventListener('DOMContentLoaded', function () {
    if (typeof Chart === 'undefined') return;

    function readJSON(id) {
        const el = document.getElementById(id);
        if (!el) return null;
        try { return JSON.parse(el.textContent); } catch (e) { return null; }
    }

    // ---- Task Status Distribution (doughnut) ----
    (function () {
        const counts = readJSON('statusChartData');
        const canvas = document.getElementById('statusChart');
        if (!counts || !canvas) return;

        const labels = ['TODO', 'In Progress', 'On Hold', 'Completed', 'Cancelled'];
        const keys = ['TODO', 'IN_PROGRESS', 'ON_HOLD', 'COMPLETED', 'CANCELLED'];
        const colors = ['#6b7280', '#2563eb', '#d97706', '#16a34a', '#dc2626'];

        new Chart(canvas, {
            type: 'doughnut',
            data: {
                labels: labels,
                datasets: [{ data: keys.map(function (k) { return counts[k] || 0; }), backgroundColor: colors }],
            },
            options: { responsive: true, plugins: { legend: { position: 'bottom' } } },
        });
    })();

    // ---- Priority Distribution (bar) ----
    (function () {
        const counts = readJSON('priorityChartData');
        const canvas = document.getElementById('priorityChart');
        if (!counts || !canvas) return;

        const labels = ['Low', 'Medium', 'High', 'Urgent'];
        const keys = ['LOW', 'MEDIUM', 'HIGH', 'URGENT'];
        const colors = ['#6b7280', '#0ea5e9', '#d97706', '#dc2626'];

        new Chart(canvas, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Tasks',
                    data: keys.map(function (k) { return counts[k] || 0; }),
                    backgroundColor: colors,
                }],
            },
            options: {
                responsive: true,
                plugins: { legend: { display: false } },
                scales: { y: { beginAtZero: true, ticks: { precision: 0 } } },
            },
        });
    })();

    // ---- Tasks by Project (pie) ----
    (function () {
        const rows = readJSON('projectChartData');
        const canvas = document.getElementById('projectChart');
        if (!rows || !rows.length || !canvas) return;

        new Chart(canvas, {
            type: 'pie',
            data: {
                labels: rows.map(function (r) { return r.name; }),
                datasets: [{
                    data: rows.map(function (r) { return r.count; }),
                    backgroundColor: rows.map(function (r) { return r.color; }),
                }],
            },
            options: { responsive: true, plugins: { legend: { position: 'bottom' } } },
        });
    })();

    // ---- Completion Trend (line) ----
    (function () {
        const trend = readJSON('trendChartData');
        const canvas = document.getElementById('trendChart');
        if (!trend || !trend.length || !canvas) return;

        new Chart(canvas, {
            type: 'line',
            data: {
                labels: trend.map(function (t) { return t.label; }),
                datasets: [{
                    label: 'Completed',
                    data: trend.map(function (t) { return t.count; }),
                    borderColor: '#16a34a',
                    backgroundColor: 'rgba(22, 163, 74, 0.12)',
                    fill: true,
                    tension: 0.3,
                    pointRadius: trend.length > 20 ? 0 : 3,
                }],
            },
            options: {
                responsive: true,
                plugins: { legend: { display: false } },
                scales: {
                    y: { beginAtZero: true, ticks: { precision: 0 } },
                    x: { ticks: { maxRotation: 0, autoSkip: true, maxTicksLimit: 10 } },
                },
            },
        });
    })();

    // ---- Hours: Estimated vs Spent (bar) ----
    (function () {
        const hours = readJSON('hoursChartData');
        const canvas = document.getElementById('hoursChart');
        if (!hours || !canvas) return;

        new Chart(canvas, {
            type: 'bar',
            data: {
                labels: ['Estimated', 'Spent'],
                datasets: [{
                    label: 'Hours',
                    data: [hours.estimated || 0, hours.spent || 0],
                    backgroundColor: ['#7c3aed', '#16a34a'],
                }],
            },
            options: {
                responsive: true,
                indexAxis: 'y',
                plugins: { legend: { display: false } },
                scales: { x: { beginAtZero: true } },
            },
        });
    })();
});
