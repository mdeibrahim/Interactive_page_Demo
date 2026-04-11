/**
 * Subject Detail Page JavaScript
 * - Accordion section toggle
 * - highlight-link click handlers
 */

(function () {
    'use strict';

    // ── ACCORDION ──
    document.querySelectorAll('.accordion-trigger').forEach(trigger => {
        trigger.addEventListener('click', function () {
            const item = this.closest('.accordion-item');
            const body = document.getElementById(this.getAttribute('aria-controls'));
            const isOpen = item.classList.contains('accordion-item--open');

            if (isOpen) {
                item.classList.remove('accordion-item--open');
                this.setAttribute('aria-expanded', 'false');
                body.hidden = true;
            } else {
                item.classList.add('accordion-item--open');
                this.setAttribute('aria-expanded', 'true');
                body.hidden = false;

                // Smooth scroll into view if needed
                setTimeout(() => {
                    const rect = body.getBoundingClientRect();
                    if (rect.bottom > window.innerHeight) {
                        body.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
                    }
                }, 50);
            }
        });
    });

    // ── HIGHLIGHT LINKS ──
    // These are <span class="highlight-link" data-content-id="X"> in the article body
    document.querySelectorAll('.highlight-link[data-content-id]').forEach(link => {
        link.setAttribute('role', 'button');
        link.setAttribute('tabindex', '0');
        link.setAttribute('title', 'Click to explore this content');

        link.addEventListener('click', function () {
            const id = this.getAttribute('data-content-id');
            if (id && window.openInteractiveModal) {
                window.openInteractiveModal(id);
            }
        });

        link.addEventListener('keydown', function (e) {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                this.click();
            }
        });
    });

})();
