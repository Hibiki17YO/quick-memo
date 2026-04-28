let memos = [];
let offset = 0;
const LIMIT = 20;
let editQuill = null;
let editingId = null;
let searchTimer = null;
let editTags = [];
let categories = [];

// ── Init ────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', async () => {
    await loadCategories();
    loadMemos();
});

// ── Categories ──────────────────────────────────────────────
async function loadCategories() {
    try {
        const res = await fetch('/api/categories');
        categories = await res.json();
        populateCategoryFilters();
    } catch (err) {
        console.error('Failed to load categories:', err);
    }
}

function populateCategoryFilters() {
    // Main filter
    const filter = document.getElementById('category-filter');
    const currentVal = filter.value;
    filter.innerHTML = '<option value="">All categories</option>';
    categories.forEach(c => {
        const opt = document.createElement('option');
        opt.value = c.id;
        opt.textContent = c.name;
        filter.appendChild(opt);
    });
    filter.value = currentVal;

    // Edit modal
    const editSel = document.getElementById('edit-category');
    if (editSel) {
        const editVal = editSel.value;
        editSel.innerHTML = '<option value="">No category</option>';
        categories.forEach(c => {
            const opt = document.createElement('option');
            opt.value = c.id;
            opt.textContent = c.name;
            editSel.appendChild(opt);
        });
        editSel.value = editVal;
    }
}

// ── Search ──────────────────────────────────────────────────
function debounceSearch() {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(() => loadMemos(), 300);
}

// ── Load memos ──────────────────────────────────────────────
async function loadMemos(append = false) {
    const q = document.getElementById('search').value;
    const sort = document.getElementById('sort').value;
    const categoryId = document.getElementById('category-filter').value;
    const tag = document.getElementById('tag-filter').value;
    const currentOffset = append ? offset : 0;

    const params = new URLSearchParams({
        q, sort, limit: LIMIT, offset: currentOffset
    });
    if (categoryId) params.set('category_id', categoryId);
    if (tag) params.set('tag', tag);

    try {
        const res = await fetch(`/api/memos?${params}`);
        const data = await res.json();
        if (!append) {
            memos = data;
            offset = 0;
        } else {
            memos = memos.concat(data);
        }
        offset += data.length;
        renderMemos();
        document.getElementById('load-more').style.display = data.length < LIMIT ? 'none' : 'block';
    } catch (err) {
        console.error('Failed to load memos:', err);
    }
}

function loadMore() {
    loadMemos(true);
}

// ── Render ──────────────────────────────────────────────────
function renderMemos() {
    const list = document.getElementById('memo-list');
    if (memos.length === 0) {
        list.innerHTML = '<div class="empty-state"><p>No memos yet. Use Ctrl+Shift+M to open the quick memo window!</p></div>';
        document.getElementById('count').textContent = '';
        document.getElementById('load-more').style.display = 'none';
        return;
    }
    list.innerHTML = memos.map(m => {
        const tags = m.tags ? m.tags.split(',').filter(Boolean) : [];
        const metaHtml = (m.category_name || tags.length) ? `<div class="memo-meta">
            ${m.category_name ? `<span class="memo-category">${escapeHtml(m.category_name)}</span>` : ''}
            ${tags.map(t => `<span class="memo-tag">${escapeHtml(t)}</span>`).join('')}
        </div>` : '';
        return `<div class="memo-card ${m.is_pinned ? 'pinned' : ''}" data-id="${m.id}">
            <div class="memo-header">
                <span class="pin-indicator">${m.is_pinned ? '\u{1F4CC}' : ''}</span>
                <h3>${escapeHtml(m.title || '(Untitled)')}</h3>
                <span class="memo-date">${formatDate(m.created_at)}</span>
            </div>
            ${metaHtml}
            <div class="memo-preview">${escapeHtml(stripHtml(m.content)).substring(0, 150)}</div>
            <div class="memo-actions">
                <button onclick="openEdit(${m.id})">Edit</button>
                <button class="delete-btn" onclick="deleteMemo(${m.id})">Delete</button>
                <button class="pin-btn" onclick="togglePin(${m.id}, ${m.is_pinned})">
                    ${m.is_pinned ? 'Unpin' : 'Pin'}
                </button>
            </div>
        </div>`;
    }).join('');
    document.getElementById('count').textContent = `${memos.length} memo${memos.length !== 1 ? 's' : ''}`;
}

// ── Delete ──────────────────────────────────────────────────
async function deleteMemo(id) {
    if (!confirm('Delete this memo?')) return;
    try {
        await fetch(`/api/memos/${id}`, { method: 'DELETE' });
        loadMemos();
    } catch (err) {
        console.error('Delete failed:', err);
    }
}

// ── Pin toggle ──────────────────────────────────────────────
async function togglePin(id, currentPinned) {
    try {
        const res = await fetch(`/api/memos/${id}`);
        const memo = await res.json();
        await fetch(`/api/memos/${id}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                title: memo.title,
                content: memo.content,
                is_pinned: currentPinned ? 0 : 1,
                category_id: memo.category_id,
                tags: memo.tags
            })
        });
        loadMemos();
    } catch (err) {
        console.error('Toggle pin failed:', err);
    }
}

// ── Edit modal ──────────────────────────────────────────────
async function openEdit(id) {
    try {
        const res = await fetch(`/api/memos/${id}`);
        const memo = await res.json();
        editingId = id;

        document.getElementById('edit-title').value = memo.title;
        document.getElementById('edit-category').value = memo.category_id || '';

        // Tags
        editTags = memo.tags ? memo.tags.split(',').filter(Boolean) : [];
        renderEditTags();

        document.getElementById('edit-modal').style.display = 'flex';

        // Create Quill
        const editorEl = document.getElementById('edit-editor');
        editorEl.innerHTML = '<div id="edit-quill"></div>';

        editQuill = new Quill('#edit-quill', {
            theme: 'snow',
            modules: {
                toolbar: [
                    ['bold', 'italic', 'underline', 'strike'],
                    [{ header: [1, 2, 3, false] }],
                    [{ list: 'ordered' }, { list: 'bullet' }],
                    ['blockquote', 'code-block'],
                    ['image'],
                    ['clean']
                ]
            },
            placeholder: 'Edit memo...'
        });

        editQuill.root.innerHTML = memo.content;

        // Image handler for edit
        editQuill.getModule('toolbar').addHandler('image', () => {
            const input = document.createElement('input');
            input.type = 'file';
            input.accept = 'image/*';
            input.click();
            input.onchange = async () => {
                const file = input.files[0];
                if (file) await insertImageEdit(file);
            };
        });

    } catch (err) {
        console.error('Open edit failed:', err);
    }
}

// Edit paste handler (document-level)
document.addEventListener('paste', async (e) => {
    if (!document.querySelector('#edit-quill .ql-editor:focus')) return;
    const items = e.clipboardData?.items;
    if (!items) return;
    for (const item of items) {
        if (item.type.startsWith('image/')) {
            e.preventDefault();
            e.stopPropagation();
            const file = item.getAsFile();
            if (file) await insertImageEdit(file);
            return;
        }
    }
}, true);

async function insertImageEdit(file) {
    const form = new FormData();
    form.append('file', file);
    form.append('memo_id', String(editingId || 0));
    try {
        const res = await fetch('/api/upload', { method: 'POST', body: form });
        const data = await res.json();
        const range = editQuill.getSelection(true);
        editQuill.insertEmbed(range.index, 'image', data.url);
        editQuill.setSelection(range.index + 1);
    } catch (err) {
        console.error('Image upload failed:', err);
    }
}

// Edit tags
function renderEditTags() {
    const wrap = document.getElementById('edit-tags-chips');
    wrap.innerHTML = editTags.map((t, i) =>
        `<span class="tag-chip">${escapeHtml(t)}<span class="remove-tag" data-i="${i}">&times;</span></span>`
    ).join('');
}

document.getElementById('edit-tags-chips').addEventListener('click', (e) => {
    const rm = e.target.closest('.remove-tag');
    if (rm) {
        editTags.splice(parseInt(rm.dataset.i), 1);
        renderEditTags();
    }
});

document.getElementById('edit-tags-input').addEventListener('keydown', (e) => {
    if (e.key === ' ' || e.key === 'Enter') {
        e.preventDefault();
        const val = e.target.value.trim();
        if (val && !editTags.includes(val)) {
            editTags.push(val);
            renderEditTags();
        }
        e.target.value = '';
    }
    if (e.key === 'Backspace' && !e.target.value && editTags.length) {
        editTags.pop();
        renderEditTags();
    }
});

document.getElementById('edit-tags-wrap').addEventListener('click', () => {
    document.getElementById('edit-tags-input').focus();
});

async function saveEdit() {
    if (!editingId || !editQuill) return;
    const content = editQuill.root.innerHTML;
    const plainText = editQuill.getText().trim();
    const title = document.getElementById('edit-title').value || plainText.split('\n')[0].substring(0, 80);
    const categoryId = document.getElementById('edit-category').value || null;
    const tagsStr = editTags.join(',');

    // Need to get current is_pinned
    const currentMemo = memos.find(m => m.id === editingId);
    const isPinned = currentMemo ? currentMemo.is_pinned : 0;

    try {
        await fetch(`/api/memos/${editingId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                title,
                content,
                is_pinned: isPinned,
                category_id: categoryId ? parseInt(categoryId) : null,
                tags: tagsStr
            })
        });
        closeModal();
        loadMemos();
    } catch (err) {
        console.error('Save edit failed:', err);
    }
}

function closeModal() {
    document.getElementById('edit-modal').style.display = 'none';
    editingId = null;
    editQuill = null;
    editTags = [];
}

// ── Settings modal ──────────────────────────────────────────
function openSettings() {
    document.getElementById('settings-modal').style.display = 'flex';
    renderCategoryList();
    loadHotkeySettings();
}

function closeSettings() {
    document.getElementById('settings-modal').style.display = 'none';
}

function renderCategoryList() {
    const list = document.getElementById('cat-list');
    if (categories.length === 0) {
        list.innerHTML = '<p style="color:#999;font-size:13px;">No categories yet.</p>';
        return;
    }
    list.innerHTML = categories.map(c => `
        <div class="cat-item" data-id="${c.id}">
            <span>${escapeHtml(c.name)}</span>
            <button onclick="editCategory(${c.id}, '${escapeHtml(c.name)}')">Edit</button>
            <button class="cat-delete" onclick="deleteCategory(${c.id})">Delete</button>
        </div>
    `).join('');
}

async function addCategory() {
    const input = document.getElementById('new-cat-name');
    const name = input.value.trim();
    if (!name) return;
    try {
        await fetch('/api/categories', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name })
        });
        input.value = '';
        await loadCategories();
        renderCategoryList();
    } catch (err) {
        console.error('Add category failed:', err);
    }
}

async function editCategory(id, oldName) {
    const newName = prompt('Category name:', oldName);
    if (!newName || newName === oldName) return;
    try {
        await fetch(`/api/categories/${id}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name: newName })
        });
        await loadCategories();
        renderCategoryList();
    } catch (err) {
        console.error('Edit category failed:', err);
    }
}

async function deleteCategory(id) {
    if (!confirm('Delete this category? Memos in this category will become uncategorized.')) return;
    try {
        await fetch(`/api/categories/${id}`, { method: 'DELETE' });
        await loadCategories();
        renderCategoryList();
        loadMemos();
    } catch (err) {
        console.error('Delete category failed:', err);
    }
}

async function loadHotkeySettings() {
    try {
        const res = await fetch('/api/settings');
        const settings = await res.json();
        document.getElementById('hotkey-toggle').value = settings.hotkey_toggle || 'ctrl+shift+m';
        document.getElementById('hotkey-quit').value = settings.hotkey_quit || 'ctrl+shift+q';
    } catch (err) {
        console.error('Load settings failed:', err);
    }
}

async function saveHotkeys() {
    const toggle = document.getElementById('hotkey-toggle').value.trim();
    const quit = document.getElementById('hotkey-quit').value.trim();
    try {
        await fetch('/api/settings', {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                settings: {
                    hotkey_toggle: toggle,
                    hotkey_quit: quit
                }
            })
        });
        alert('Hotkeys saved. Restart the app to apply changes.');
    } catch (err) {
        console.error('Save hotkeys failed:', err);
    }
}

// Close modals on click outside
document.addEventListener('click', (e) => {
    if (e.target.classList.contains('modal')) {
        if (e.target.id === 'edit-modal') closeModal();
        if (e.target.id === 'settings-modal') closeSettings();
    }
});

// ESC to close
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        closeModal();
        closeSettings();
    }
});

// Enter in new category input
document.getElementById('new-cat-name').addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
        e.preventDefault();
        addCategory();
    }
});

// ── Helpers ─────────────────────────────────────────────────
function stripHtml(html) {
    const tmp = document.createElement('div');
    tmp.innerHTML = html;
    return tmp.textContent || '';
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function formatDate(iso) {
    try {
        const d = new Date(iso);
        return d.toLocaleDateString('zh-CN', {
            year: 'numeric', month: '2-digit', day: '2-digit',
            hour: '2-digit', minute: '2-digit'
        });
    } catch {
        return iso;
    }
}
