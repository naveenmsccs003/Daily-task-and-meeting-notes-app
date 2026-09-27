// Quick status update: change the dropdown in the task table without
// opening the full edit form or reloading the page.

function showQuickToast(message, isError) {
    const container = document.querySelector('.flash-container') || (function () {
        const div = document.createElement('div');
        div.className = 'flash-container';
        const content = document.querySelector('.content');
        if (content) content.prepend(div);
        return div;
    })();

    const alert = document.createElement('div');
    alert.className = 'alert alert-' + (isError ? 'danger' : 'success') + ' alert-dismissible fade show';
    alert.setAttribute('role', 'alert');
    alert.innerHTML = message + '<button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>';
    container.appendChild(alert);
    setTimeout(function () { alert.remove(); }, 4000);
}

document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('.status-select').forEach(function (select) {
        let previousValue = select.value;
        select.addEventListener('change', function () {
            const taskId = select.dataset.taskId;
            const newStatus = select.value;
            select.disabled = true;

            fetch('/tasks/' + taskId + '/status', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest',
                    'X-CSRFToken': getCsrfToken(),
                },
                body: JSON.stringify({ status: newStatus }),
            })
                .then(function (response) {
                    return response.json().then(function (data) {
                        return { ok: response.ok, data: data };
                    });
                })
                .then(function (result) {
                    select.disabled = false;
                    if (result.ok && result.data.success) {
                        showQuickToast(result.data.message, false);
                        previousValue = newStatus;
                    } else {
                        select.value = previousValue;
                        showQuickToast(result.data.message || 'Unable to update task.', true);
                    }
                })
                .catch(function () {
                    select.disabled = false;
                    select.value = previousValue;
                    showQuickToast('Network error. Please try again.', true);
                });
        });
    });
});
