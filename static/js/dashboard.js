document.addEventListener('DOMContentLoaded', function () {
    const dataEl = document.getElementById('statusChartData');
    const canvas = document.getElementById('statusChart');
    if (!dataEl || !canvas || typeof Chart === 'undefined') return;

    const counts = JSON.parse(dataEl.textContent);
    const labels = ['TODO', 'In Progress', 'On Hold', 'Completed', 'Cancelled'];
    const keys = ['TODO', 'IN_PROGRESS', 'ON_HOLD', 'COMPLETED', 'CANCELLED'];
    const colors = ['#6b7280', '#2563eb', '#d97706', '#16a34a', '#dc2626'];

    new Chart(canvas, {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [{
                data: keys.map(function (k) { return counts[k] || 0; }),
                backgroundColor: colors,
            }],
        },
        options: {
            responsive: true,
            plugins: {
                legend: { position: 'bottom' },
            },
        },
    });
});
