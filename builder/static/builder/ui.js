/**
 * UI enhancements: confirmation dialogs, loading states, auto-dismiss messages.
 * Loaded on every page via base.html.
 */
(function () {
    'use strict';

    // 1a. Confirmation dialogs — forms with data-confirm="..." prompt before submit
    document.addEventListener('submit', function (e) {
        var form = e.target;
        var message = form.getAttribute('data-confirm');
        if (message && !window.confirm(message)) {
            e.preventDefault();
        }
    });

    // 1b. Loading states — disable button and swap text on form submit
    document.addEventListener('submit', function (e) {
        var form = e.target;
        if (e.defaultPrevented) return;

        var btn = form.querySelector('button[data-loading-text]');
        if (!btn) return;

        btn.disabled = true;
        btn.textContent = btn.getAttribute('data-loading-text');
        btn.classList.add('is-loading');
    });

    // 1c. Auto-dismiss messages — fade after 5s, click to dismiss immediately
    var stack = document.querySelector('[data-autodismiss]');
    if (stack) {
        var msgs = stack.querySelectorAll('.message');

        function dismiss(el) {
            el.classList.add('is-fading');
            el.addEventListener('transitionend', function () {
                el.remove();
            });
        }

        msgs.forEach(function (msg) {
            msg.style.cursor = 'pointer';
            msg.addEventListener('click', function () {
                dismiss(msg);
            });

            setTimeout(function () {
                if (msg.parentNode) dismiss(msg);
            }, 5000);
        });
    }
})();
