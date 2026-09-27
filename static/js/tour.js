// First-time-user onboarding tour. Auto-runs once (per browser) on a
// user's first Dashboard visit, and can be replayed anytime via the
// "Take a Tour" sidebar link. Plain DOM/CSS — no tour library.
(function () {
    var STORAGE_KEY = 'dtmt_tour_completed_v1';

    var steps = [
        {
            selector: '.sidebar-brand',
            title: 'Welcome!',
            text: 'This replaces your spreadsheet for tracking daily tasks and meetings. Let\'s take a 30-second look around.',
            placement: 'right',
        },
        {
            selector: '.sidebar-nav',
            title: 'Navigation',
            text: 'Use the sidebar to move between your Dashboard, Tasks, Meetings, and Reports.',
            placement: 'right',
        },
        {
            selector: '.quick-actions',
            title: 'Quick Actions',
            text: 'Add a new task or meeting in a couple of clicks, right from here.',
            placement: 'bottom',
        },
        {
            selector: '.summary-cards',
            title: 'Today at a Glance',
            text: 'These cards summarize your tasks and meetings for the selected period. Click any card to jump to that filtered list.',
            placement: 'bottom',
        },
        {
            selector: '#statusChart',
            title: 'Status Distribution',
            text: 'This chart shows how your tasks are split across statuses for the selected date range.',
            placement: 'top',
        },
    ];

    var currentStep = 0;
    var overlay = null;
    var tooltip = null;

    function clearHighlight() {
        var highlighted = document.querySelectorAll('.tour-highlight');
        for (var i = 0; i < highlighted.length; i++) {
            highlighted[i].classList.remove('tour-highlight');
        }
    }

    function positionTooltip(rect, placement) {
        var top, left;
        if (placement === 'right') {
            top = rect.top + window.scrollY;
            left = rect.right + window.scrollX + 16;
        } else if (placement === 'top') {
            top = rect.top + window.scrollY - 12;
            left = rect.left + window.scrollX;
            tooltip.style.transform = 'translateY(-100%)';
        } else {
            top = rect.bottom + window.scrollY + 12;
            left = rect.left + window.scrollX;
            tooltip.style.transform = '';
        }
        tooltip.style.top = Math.max(8, top) + 'px';
        tooltip.style.left = Math.max(16, Math.min(left, window.innerWidth - 316)) + 'px';
    }

    function endTour() {
        clearHighlight();
        if (overlay) { overlay.remove(); overlay = null; }
        if (tooltip) { tooltip.remove(); tooltip = null; }
        document.body.classList.remove('tour-active');
        try { localStorage.setItem(STORAGE_KEY, '1'); } catch (e) { /* private mode: ignore */ }
    }

    function showStep(index) {
        clearHighlight();
        var step = steps[index];
        var target = document.querySelector(step.selector);

        if (!target) {
            if (index < steps.length - 1) { showStep(index + 1); } else { endTour(); }
            return;
        }

        target.classList.add('tour-highlight');
        target.scrollIntoView({ block: 'center', behavior: 'smooth' });

        var rect = target.getBoundingClientRect();
        var isLast = index === steps.length - 1;

        tooltip.innerHTML =
            '<div class="tour-step-count">Step ' + (index + 1) + ' of ' + steps.length + '</div>' +
            '<h5></h5><p></p>' +
            '<div class="tour-actions">' +
            (index > 0 ? '<button type="button" class="btn btn-sm btn-outline-secondary" id="tourPrev">Back</button>' : '<span></span>') +
            '<div>' +
            '<button type="button" class="btn btn-sm btn-link" id="tourSkip">Skip</button>' +
            '<button type="button" class="btn btn-sm btn-primary" id="tourNext">' + (isLast ? 'Finish' : 'Next') + '</button>' +
            '</div>' +
            '</div>';
        tooltip.querySelector('h5').textContent = step.title;
        tooltip.querySelector('p').textContent = step.text;

        positionTooltip(rect, step.placement);

        document.getElementById('tourNext').addEventListener('click', function () {
            if (isLast) { endTour(); } else { showStep(index + 1); }
        });
        var prevBtn = document.getElementById('tourPrev');
        if (prevBtn) {
            prevBtn.addEventListener('click', function () { showStep(index - 1); });
        }
        document.getElementById('tourSkip').addEventListener('click', endTour);
    }

    function startTour() {
        if (document.body.dataset.page !== 'dashboard') {
            window.location.href = '/dashboard?tour=1';
            return;
        }
        currentStep = 0;
        overlay = document.createElement('div');
        overlay.className = 'tour-overlay';
        document.body.appendChild(overlay);

        tooltip = document.createElement('div');
        tooltip.className = 'tour-tooltip';
        document.body.appendChild(tooltip);

        document.body.classList.add('tour-active');
        showStep(0);
    }

    document.addEventListener('DOMContentLoaded', function () {
        var replayBtn = document.getElementById('startTourBtn');
        if (replayBtn) {
            replayBtn.addEventListener('click', function (e) {
                e.preventDefault();
                startTour();
            });
        }

        if (document.body.dataset.page === 'dashboard') {
            var forceTour = new URLSearchParams(window.location.search).get('tour') === '1';
            var seen = false;
            try { seen = localStorage.getItem(STORAGE_KEY) === '1'; } catch (e) { seen = true; }
            if (forceTour || !seen) {
                setTimeout(startTour, 500);
            }
        }
    });
})();
