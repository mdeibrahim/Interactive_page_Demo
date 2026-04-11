/**
 * Main JavaScript — Modal + General UI
 * Interactive Teaching Platform
 */

(function () {
    'use strict';

    // ── Modal Elements ──
    const modal       = document.getElementById('contentModal');
    const modalTitle  = document.getElementById('modalTitle');
    const modalBody   = document.getElementById('modalBody');
    const modalClose  = document.getElementById('modalClose');

    if (!modal) return;

    // ── Open Modal ──
    function openModal(contentId) {
        // Get API URL from data script tag if available, else build manually
        const dataEl = document.getElementById('interactiveData');
        let apiUrl;

        if (dataEl) {
            const data = JSON.parse(dataEl.textContent);
            apiUrl = data.apiUrl.replace('/0/', `/${contentId}/`);
        } else {
            apiUrl = `/api/content/${contentId}/`;
        }

        // Show loading state
        modalTitle.textContent = 'Loading…';
        modalBody.innerHTML = `
            <div class="modal-loading">
                <div class="spinner"></div>
                <p>Loading content…</p>
            </div>`;

        modal.classList.add('modal--active');
        document.body.style.overflow = 'hidden';
        modalClose.focus();

        // Fetch content
        fetch(apiUrl)
            .then(res => {
                if (!res.ok) throw new Error(`HTTP ${res.status}`);
                return res.json();
            })
            .then(data => renderModal(data))
            .catch(err => {
                modalTitle.textContent = 'Error';
                modalBody.innerHTML = `
                    <div class="modal-error">
                        <i class="fa-solid fa-circle-exclamation"></i>
                        <p>Failed to load content. ${err.message}</p>
                    </div>`;
            });
    }

    // ── Render Modal Content ──
    function renderModal(data) {
        modalTitle.textContent = data.title || 'Content';

        let html = '';

        switch (data.content_type) {
            case 'text':
                html = `<div class="modal-text-content">${data.text_content || '<em>No text content.</em>'}</div>`;
                break;

            case 'image':
                if (data.image_url) {
                    html = `
                        <div class="modal-image-wrap">
                            <img src="${data.image_url}" alt="${escHtml(data.title)}" class="modal-image" loading="lazy">
                        </div>`;
                } else {
                    html = noContentHtml('image');
                }
                break;

            case 'audio':
                if (data.audio_url) {
                    html = `
                        <div class="modal-audio-wrap">
                            <p style="margin-bottom:16px;color:var(--text-secondary);">
                                <i class="fa-solid fa-headphones"></i> Click play to listen:
                            </p>
                            <audio controls class="modal-audio" autoplay>
                                <source src="${data.audio_url}">
                                Your browser does not support audio.
                            </audio>
                        </div>`;
                } else {
                    html = noContentHtml('audio');
                }
                break;

            case 'video':
                if (data.video_url) {
                    html = `
                        <div class="modal-video-wrap">
                            <video controls class="modal-video" autoplay muted>
                                <source src="${data.video_url}">
                                Your browser does not support video.
                            </video>
                        </div>`;
                } else {
                    html = noContentHtml('video');
                }
                break;

            case 'youtube':
                if (data.youtube_embed_url) {
                    html = `
                        <div class="modal-youtube-wrap">
                            <iframe
                                src="${data.youtube_embed_url}?autoplay=1"
                                title="${escHtml(data.title)}"
                                allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                                allowfullscreen>
                            </iframe>
                        </div>`;
                } else {
                    html = noContentHtml('youtube');
                }
                break;

            default:
                html = `<p>Unknown content type: ${escHtml(data.content_type)}</p>`;
        }

        modalBody.innerHTML = html;
    }

    function noContentHtml(type) {
        return `
            <div class="modal-error">
                <i class="fa-solid fa-circle-exclamation"></i>
                <p>No ${type} content has been uploaded yet.</p>
            </div>`;
    }

    function escHtml(str) {
        return String(str).replace(/[&<>"']/g, m => ({
            '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
        }[m]));
    }

    // ── Close Modal ──
    function closeModal() {
        modal.classList.remove('modal--active');
        document.body.style.overflow = '';

        // Stop any playing media
        modal.querySelectorAll('audio, video, iframe').forEach(el => {
            if (el.tagName === 'IFRAME') {
                el.src = el.src; // reload to stop YT
            } else {
                el.pause();
            }
        });

        modalBody.innerHTML = `<div class="modal-loading"><div class="spinner"></div><p>Loading content…</p></div>`;
        modalTitle.textContent = '';
    }

    modalClose.addEventListener('click', closeModal);

    modal.addEventListener('click', function (e) {
        if (e.target === modal) closeModal();
    });

    document.addEventListener('keydown', function (e) {
        if (e.key === 'Escape' && modal.classList.contains('modal--active')) closeModal();
    });

    // ── Attach click events to interactive elements ──
    function attachInteractiveClicks() {
        // Toolbar buttons
        document.querySelectorAll('[data-content-id]').forEach(el => {
            el.addEventListener('click', function (e) {
                e.preventDefault();
                const id = this.getAttribute('data-content-id');
                if (id) openModal(id);
            });
        });
    }

    // Run on DOM ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', attachInteractiveClicks);
    } else {
        attachInteractiveClicks();
    }

    // Expose for dynamic content
    window.openInteractiveModal = openModal;

})();
