document.addEventListener('DOMContentLoaded', function () {
    function getCookie(name) {
        const value = `; ${document.cookie}`;
        const parts = value.split(`; ${name}=`);
        if (parts.length === 2) return parts.pop().split(';').shift();
    }

    function getModuleIdFromAdminUrl() {
        // matches /admin/content/module/<id>/change/
        const m = window.location.pathname.match(/\/admin\/content\/module\/(\d+)\/change\//);
        if (m) return m[1];
        return null;
    }

    async function uploadFileToApi(file, mediaType, moduleId) {
        if (!moduleId) moduleId = getModuleIdFromAdminUrl() || prompt('Enter module ID to attach this media to:');
        if (!moduleId) throw new Error('Module ID required');

        const form = new FormData();
        form.append('content_type', mediaType);
        form.append('title', file.name);
        if (mediaType === 'image') form.append('image', file);
        if (mediaType === 'audio') form.append('audio', file);
        if (mediaType === 'video') form.append('video', file);

        const resp = await fetch(`/api/module/${moduleId}/ic/create/`, {
            method: 'POST',
            body: form,
            credentials: 'same-origin',
            headers: {
                'X-CSRFToken': getCookie('csrftoken') || ''
            }
        });

        if (!resp.ok) {
            const txt = await resp.text();
            throw new Error('Upload failed: ' + txt);
        }

        const data = await resp.json();
        if (!data.ok || !data.ic) throw new Error('Upload did not return content data');
        return data.ic;
    }

    function handleFileUpload(file, mediaType, editor) {
        if (!file) return;
        const moduleId = getModuleIdFromAdminUrl();
            uploadFileToApi(file, mediaType, moduleId).then(function (ic) {
                // on success, wrap selected text with highlight-link referencing the new CourseContent id
                const sel = window.getSelection();
                const span = document.createElement('span');
                span.className = 'highlight-link highlight-link--blue';
                span.dataset.contentId = String(ic.id);

                const selectedText = (sel && sel.rangeCount > 0) ? sel.toString() : '';
                span.textContent = selectedText || ic.title || 'Media';

                if (!sel || sel.rangeCount === 0) {
                    editor.appendChild(span);
                    editor.focus();
                    return;
                }

                const range = sel.getRangeAt(0);
                if (!editor.contains(range.commonAncestorContainer)) {
                    editor.appendChild(span);
                    editor.focus();
                    return;
                }

                range.deleteContents();
                range.insertNode(span);
                // move cursor after inserted node
                range.setStartAfter(span);
                sel.removeAllRanges();
                sel.addRange(range);
                editor.focus();
            }).catch(function (err) {
                alert('Upload error: ' + (err.message || err));
        });
    }

    function createToolbar() {
        const toolbar = document.createElement('div');
        toolbar.className = 'admin-rte-toolbar';

        const buttons = [
            { cmd: 'bold', icon: 'B' },
            { cmd: 'italic', icon: 'I' },
            { cmd: 'underline', icon: 'U' },
            { cmd: 'insertUnorderedList', icon: '• List' },
            { cmd: 'insertOrderedList', icon: '1. List' },
            { cmd: 'createLink', icon: 'Link' },
            { cmd: 'insertImage', icon: 'Img' },
            { cmd: 'insertAudio', icon: '♫' },
            { cmd: 'insertVideo', icon: '▶' },
        ];

        buttons.forEach(function (b) {
            const btn = document.createElement('button');
            btn.type = 'button';
            btn.className = 'admin-rte-btn';
            btn.textContent = b.icon;
            btn.dataset.cmd = b.cmd;
            btn.addEventListener('click', function () {
                const editor = toolbar.nextElementSibling;
                if (!editor) return;

                if (b.cmd === 'createLink') {
                    const url = prompt('Enter URL');
                    if (!url) return;
                    document.execCommand('createLink', false, url);
                    editor.focus();
                    return;
                }

                // media insert: prefer file upload via hidden inputs, fallback to URL prompt
                if (b.cmd === 'insertImage' || b.cmd === 'insertAudio' || b.cmd === 'insertVideo') {
                    const wrapper = toolbar.parentNode;
                    const fileInputs = wrapper && wrapper._fileInputs;
                    const which = b.cmd === 'insertImage' ? 'image' : (b.cmd === 'insertAudio' ? 'audio' : 'video');

                    if (fileInputs && fileInputs[which]) {
                        fileInputs[which].click();
                        return;
                    }

                    const url = prompt('Enter media URL (absolute or /media/ path)');
                    if (!url) return;

                    const sel = window.getSelection();
                    if (!sel || sel.rangeCount === 0) {
                        // insert at end
                        editor.insertAdjacentHTML('beforeend', createMediaHtml(b.cmd, url, ''));
                        editor.focus();
                        return;
                    }

                    const range = sel.getRangeAt(0);
                    if (!editor.contains(range.commonAncestorContainer)) {
                        editor.insertAdjacentHTML('beforeend', createMediaHtml(b.cmd, url, ''));
                        editor.focus();
                        return;
                    }

                    const selectedText = range.toString();
                    const mediaNode = htmlToNode(createMediaHtml(b.cmd, url, selectedText));
                    range.deleteContents();
                    range.insertNode(mediaNode);
                    sel.removeAllRanges();
                    editor.focus();
                    return;
                }

                document.execCommand(b.cmd, false, null);
                editor.focus();
            });
            toolbar.appendChild(btn);
        });

        return toolbar;
    }

    function createMediaHtml(cmd, url, text) {
        if (cmd === 'insertImage') {
            const alt = escapeHtml(text || '');
            return `<img src="${escapeAttr(url)}" alt="${alt}" style="max-width:100%;height:auto;"/>`;
        }
        if (cmd === 'insertAudio') {
            const caption = escapeHtml(text || '');
            return `<audio controls src="${escapeAttr(url)}">${caption}</audio>`;
        }
        if (cmd === 'insertVideo') {
            return `<video controls src="${escapeAttr(url)}" style="max-width:100%;height:auto;"></video>`;
        }
        return '';
    }

    function htmlToNode(html) {
        const template = document.createElement('template');
        template.innerHTML = html.trim();
        return template.content.firstChild;
    }

    function escapeAttr(s) {
        return String(s).replace(/"/g, '&quot;');
    }

    function escapeHtml(text) {
        const d = document.createElement('div');
        d.textContent = text || '';
        return d.innerHTML;
    }

    document.querySelectorAll('textarea.rte-enabled').forEach(function (ta) {
        // hide original textarea but keep it for form submission
        ta.style.display = 'none';

        const wrapper = document.createElement('div');
        wrapper.className = 'admin-rte-wrapper';

        const toolbar = createToolbar();
        const editor = document.createElement('div');
        editor.className = 'admin-rte-editor';
        editor.contentEditable = 'true';
        editor.innerHTML = ta.value ? ta.value.replace(/\n/g, '<br>') : '';

        // sync back to textarea before submit
        const form = ta.closest('form');
        if (form) {
            form.addEventListener('submit', function () {
                ta.value = editor.innerHTML;
            });
        }

            wrapper.appendChild(toolbar);
            wrapper.appendChild(editor);
            // cache module id for quicker uploads
            wrapper.dataset.moduleId = getModuleIdFromAdminUrl() || '';
        ta.parentNode.insertBefore(wrapper, ta);

        // hidden file inputs for uploads
        const fileImage = document.createElement('input');
        fileImage.type = 'file';
        fileImage.accept = 'image/*';
        fileImage.style.display = 'none';

        const fileAudio = document.createElement('input');
        fileAudio.type = 'file';
        fileAudio.accept = 'audio/*';
        fileAudio.style.display = 'none';

        const fileVideo = document.createElement('input');
        fileVideo.type = 'file';
        fileVideo.accept = 'video/*';
        fileVideo.style.display = 'none';

        document.body.appendChild(fileImage);
        document.body.appendChild(fileAudio);
        document.body.appendChild(fileVideo);

        fileImage.addEventListener('change', function (e) { handleFileUpload(e.target.files[0], 'image', editor); });
        fileAudio.addEventListener('change', function (e) { handleFileUpload(e.target.files[0], 'audio', editor); });
        fileVideo.addEventListener('change', function (e) { handleFileUpload(e.target.files[0], 'video', editor); });

        // expose file inputs via wrapper for toolbar handlers
        wrapper._fileInputs = { image: fileImage, audio: fileAudio, video: fileVideo };
    });
});
