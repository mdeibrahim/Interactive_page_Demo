/* editor.js */
document.addEventListener('DOMContentLoaded', () => {
    
    // --- Data ---
    const editorDataEl = document.getElementById('editorData');
    if (!editorDataEl) return;
    const config = JSON.parse(editorDataEl.textContent);
    
    // --- Toolbar Formatting ---
    const formatButtons = document.querySelectorAll('.rte-btn[data-cmd]');
    
    // Check formatting at cursor position
    document.getElementById('rteContent').addEventListener('keyup', checkFormatStatus);
    document.getElementById('rteContent').addEventListener('mouseup', checkFormatStatus);
    document.getElementById('rteContent').addEventListener('click', checkFormatStatus);

    function checkFormatStatus(e) {
        if (!window.getSelection().rangeCount) return;
        formatButtons.forEach(btn => {
            const command = btn.getAttribute('data-cmd');
            if (document.queryCommandState(command)) {
                btn.classList.add('active');
            } else {
                btn.classList.remove('active');
            }
        });
    }

    formatButtons.forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.preventDefault();
            const cmd = btn.getAttribute('data-cmd');
            document.execCommand(cmd, false, null);
            checkFormatStatus();
        });
    });

    // --- Subject Title sync & Save ---
    const titleInput = document.getElementById('editorTitleInput');
    const saveBtn = document.getElementById('btn-save-body');
    const editorStatus = document.getElementById('editorStatus');
    const rteContent = document.getElementById('rteContent');

    saveBtn.addEventListener('click', async () => {
        saveBtn.disabled = true;
        editorStatus.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Saving...';
        editorStatus.style.color = '#3b82f6';

        try {
            const res = await fetch(config.saveUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': config.csrfToken
                },
                body: JSON.stringify({
                    title: titleInput.value,
                    body_content: rteContent.innerHTML
                })
            });
            const data = await res.json();
            if (data.ok) {
                editorStatus.innerHTML = '<i class="fa-solid fa-circle-check"></i> Saved';
                editorStatus.style.color = '#16a34a';
                setTimeout(() => {
                    editorStatus.innerHTML = '';
                }, 3000);
            }
        } catch (e) {
            editorStatus.innerHTML = '<i class="fa-solid fa-triangle-exclamation"></i> Error';
            editorStatus.style.color = '#ef4444';
        }
        saveBtn.disabled = false;
    });

    // Handle Link Media
    const btnLinkMedia = document.getElementById('btn-insert-link');
    const insertLinkModal = document.getElementById('insertLinkModal');
    const linkPickerList = document.getElementById('linkPickerList');
    const insertLinkConfirm = document.getElementById('insertLinkConfirm');
    
    let savedSelection = null;
    let selectedMediaId = null;

    btnLinkMedia.addEventListener('click', () => {
        const sel = window.getSelection();
        if(!sel.rangeCount || sel.isCollapsed) {
            alert("Please select some text first to create a link.");
            return;
        }

        savedSelection = sel.getRangeAt(0).cloneRange();

        // Populate media list
        const mediaCards = document.querySelectorAll('#icList .ic-item');
        linkPickerList.innerHTML = '';
        
        if(mediaCards.length === 0) {
            linkPickerList.innerHTML = '<div style="padding: 15px; color: #6b7280; text-align: center;">No media available. Please add some on the right panel first.</div>';
            insertLinkConfirm.disabled = true;
        } else {
            mediaCards.forEach(card => {
                const id = card.getAttribute('data-ic-id');
                const title = card.querySelector('.ic-item-title').textContent;
                const type = card.querySelector('.ic-item-type').textContent;
                const icon = card.querySelector('.ic-item-icon').innerHTML;
                
                const div = document.createElement('div');
                div.className = 'link-picker-item';
                div.dataset.id = id;
                div.innerHTML = `
                    <div style="width: 32px; height: 32px; display: flex; align-items: center; justify-content: center; background: #f1f5f9; border-radius: 6px; color: var(--brand); flex-shrink: 0;">${icon}</div>
                    <div style="flex: 1;">
                        <div style="font-weight: 600; font-size: 0.95rem;">${title}</div>
                        <div style="font-size: 0.8rem; color: #6b7280;">${type}</div>
                    </div>
                `;
                div.addEventListener('click', () => {
                    document.querySelectorAll('.link-picker-item').forEach(el => el.classList.remove('selected'));
                    div.classList.add('selected');
                    selectedMediaId = id;
                    insertLinkConfirm.disabled = false;
                });
                linkPickerList.appendChild(div);
            });
        }
        
        insertLinkModal.hidden = false;
    });

    document.getElementById('insertLinkClose').addEventListener('click', () => insertLinkModal.hidden = true);
    document.getElementById('insertLinkCancel').addEventListener('click', () => insertLinkModal.hidden = true);

    insertLinkConfirm.addEventListener('click', () => {
        if(!selectedMediaId || !savedSelection) return;
        
        const styleSelect = document.querySelector('input[name="link_style"]:checked').value;
        const linkClass = styleSelect === 'blue_bold' ? 'highlight-link link-media-blue' : 'highlight-link link-media-red';
        
        // Restore selection
        const sel = window.getSelection();
        sel.removeAllRanges();
        sel.addRange(savedSelection);
        
        // Remove formatting and insert HTML
        document.execCommand("insertHTML", false, `<span class="${linkClass}" data-content-id="${selectedMediaId}">${savedSelection.toString()}</span>`);
        
        insertLinkModal.hidden = true;
        savedSelection = null;
        selectedMediaId = null;
    });

    // Interactive Content Modals & API setup
    const icModal = document.getElementById('icModal');
    const icForm = document.getElementById('icForm');
    
    document.getElementById('btn-add-ic').addEventListener('click', () => {
        icForm.reset();
        document.getElementById('icFormId').value = '';
        document.getElementById('icModalTitle').innerHTML = '<i class="fa-solid fa-wand-magic-sparkles"></i> Add Media Item';
        document.querySelectorAll('.type-btn').forEach(b => b.classList.remove('active'));
        document.querySelector('.type-btn[data-type="text"]').classList.add('active');
        document.getElementById('icType').value = 'text';
        updateIcFormSections('text');
        icModal.hidden = false;
    });

    document.getElementById('icModalClose').addEventListener('click', () => icModal.hidden = true);
    document.getElementById('icModalCancel').addEventListener('click', () => icModal.hidden = true);

    document.querySelectorAll('.type-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.type-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            const type = btn.getAttribute('data-type');
            document.getElementById('icType').value = type;
            updateIcFormSections(type);
        });
    });

    function updateIcFormSections(type) {
        ['text', 'image', 'audio', 'video', 'youtube'].forEach(t => {
            document.getElementById(`field${t.charAt(0).toUpperCase() + t.slice(1)}`).hidden = (t !== type);
        });
    }

    icForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const id = document.getElementById('icFormId').value;
        const url = id ? `${config.icUpdateBase}${id}/update/` : config.icCreateUrl;
        
        const fd = new FormData(icForm);
        fd.append('content_type', document.getElementById('icType').value);
        if(document.getElementById('icType').value === 'text') {
            fd.append('text_content', document.getElementById('icTextContent').value);
        }

        try {
            const res = await fetch(url, {
                method: 'POST',
                headers: { 'X-CSRFToken': config.csrfToken },
                body: fd
            });
            if (res.ok) {
                window.location.reload(); // Quickest way to update UI
            }
        } catch (err) {
            console.error(err);
            alert("Error saving Media Item");
        }
    });

    // Accordion Modals & API setup
    const accModal = document.getElementById('accModal');
    const accForm = document.getElementById('accForm');

    document.getElementById('btn-add-accordion').addEventListener('click', () => {
        accForm.reset();
        document.getElementById('accFormId').value = '';
        document.getElementById('accModalTitle').innerHTML = '<i class="fa-solid fa-layer-group"></i> Add Accordion Section';
        accModal.hidden = false;
    });

    document.getElementById('accModalClose').addEventListener('click', () => accModal.hidden = true);
    document.getElementById('accModalCancel').addEventListener('click', () => accModal.hidden = true);

    accForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const id = document.getElementById('accFormId').value;
        const url = id ? `${config.accUpdateBase}${id}/update/` : config.accCreateUrl;
        
        try {
            const res = await fetch(url, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': config.csrfToken
                },
                body: JSON.stringify({
                    title: document.getElementById('accTitle').value,
                    content: document.getElementById('accContent').value,
                    is_open_by_default: document.getElementById('accIsOpen').checked
                })
            });
            if (res.ok) {
                window.location.reload();
            }
        } catch(err) {
            console.error(err);
            alert('Error saving Accordion section');
        }
    });

    // Delete handlers
    document.querySelectorAll('.ic-delete-btn').forEach(btn => {
        btn.addEventListener('click', async () => {
            if(!confirm("Are you sure you want to delete this media item?")) return;
            const id = btn.getAttribute('data-ic-id');
            try {
                const res = await fetch(`${config.icDeleteBase}${id}/delete/`, {
                    method: 'POST',
                    headers: { 'X-CSRFToken': config.csrfToken }
                });
                if(res.ok) window.location.reload();
            } catch(e) { console.error(e); }
        });
    });

    document.querySelectorAll('.acc-delete-btn').forEach(btn => {
        btn.addEventListener('click', async () => {
            if(!confirm("Are you sure you want to delete this section?")) return;
            const id = btn.getAttribute('data-sec-id');
            try {
                const res = await fetch(`${config.accDeleteBase}${id}/delete/`, {
                    method: 'POST',
                    headers: { 'X-CSRFToken': config.csrfToken }
                });
                if(res.ok) window.location.reload();
            } catch(e) { console.error(e); }
        });
    });

    // Editing existing items
    document.querySelectorAll('.ic-edit-btn').forEach(btn => {
        btn.addEventListener('click', async () => {
            // Need API to fetch single IC. For simplicity, we just reload it in a real app
            // However, we don't have a single GET endpoint. We can parse the DOM or fetch from subject API
            const id = btn.getAttribute('data-ic-id');
            alert("Edit modal currently requires fetching data. For now, delete and recreate.");
        });
    });

    document.querySelectorAll('.acc-edit-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            alert("Edit modal currently requires fetching data. For now, delete and recreate.");
        });
    });

});
