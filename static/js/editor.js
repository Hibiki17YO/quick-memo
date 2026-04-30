// ── Theme ───────────────────────────────────────────────────
function getTheme() {
    return localStorage.getItem('memo-theme') || 'light';
}

function applyTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    document.getElementById('theme-btn').textContent = theme === 'light' ? 'Dark' : 'Light';
    const api = window.pywebview?.api;
    if (api?.set_dark_titlebar) {
        api.set_dark_titlebar(theme === 'dark');
    }
}

function toggleTheme() {
    const next = getTheme() === 'light' ? 'dark' : 'light';
    localStorage.setItem('memo-theme', next);
    applyTheme(next);
}

applyTheme(getTheme());

// ── Window controls (pywebview JS API) ──────────────────────
function pyApi() {
    return window.pywebview?.api;
}

async function togglePin() {
    const api = pyApi();
    if (!api?.toggle_on_top) return;
    const onTop = await api.toggle_on_top();
    document.getElementById('pin-btn').classList.toggle('active', onTop);
}

async function openManagement() {
    const api = pyApi();
    if (api?.open_management_page) {
        await api.open_management_page();
    } else {
        window.open('http://127.0.0.1:18080', '_blank');
    }
}

window.addEventListener('pywebviewready', async () => {
    const api = pyApi();
    if (api?.get_state) {
        const state = await api.get_state();
        document.getElementById('pin-btn').classList.toggle('active', state.is_on_top);
    }
    if (api?.set_dark_titlebar) {
        api.set_dark_titlebar(getTheme() === 'dark');
    }
});

// ── Quill Editor (init after settings load) ─────────────────
let quill = null;
let tags = [];

async function initEditor() {
    let toolbarKeys = window.TOOLBAR_DEFAULT;
    try {
        const res = await fetch('/api/settings');
        const settings = await res.json();
        if (settings.editor_toolbar) {
            try {
                const parsed = JSON.parse(settings.editor_toolbar);
                if (Array.isArray(parsed) && parsed.length) toolbarKeys = parsed;
            } catch {}
        }
    } catch (err) {
        console.warn('settings load failed, using defaults', err);
    }

    const toolbarConfig = window.buildQuillToolbar(toolbarKeys);

    quill = new Quill('#editor', {
        theme: 'snow',
        modules: {
            toolbar: toolbarConfig,
        },
        placeholder: 'Write something...'
    });

    // Image handler
    const tb = quill.getModule('toolbar');
    if (tb) {
        tb.addHandler('image', () => {
            const input = document.createElement('input');
            input.type = 'file';
            input.accept = 'image/*';
            input.click();
            input.onchange = async () => {
                if (input.files[0]) await insertImage(input.files[0]);
            };
        });
    }

    quill.root.addEventListener('keydown', (e) => {
        if (e.ctrlKey && e.key === 'Enter') { e.preventDefault(); saveMemo(); }
    });
}

initEditor();

// ── Tags ────────────────────────────────────────────────────
function renderTags() {
    const wrap = document.getElementById('tags-chips');
    wrap.innerHTML = tags.map((t, i) =>
        `<span class="tag-chip">${esc(t)}<span class="remove-tag" data-i="${i}">&times;</span></span>`
    ).join('');
}

function esc(text) {
    const d = document.createElement('div');
    d.textContent = text;
    return d.innerHTML;
}

document.getElementById('tags-chips').addEventListener('click', (e) => {
    const rm = e.target.closest('.remove-tag');
    if (rm) { tags.splice(parseInt(rm.dataset.i), 1); renderTags(); }
});

document.getElementById('tags-input').addEventListener('keydown', (e) => {
    if (e.key === ' ' || e.key === 'Enter') {
        e.preventDefault();
        const v = e.target.value.trim();
        if (v && !tags.includes(v)) { tags.push(v); renderTags(); }
        e.target.value = '';
    }
    if (e.key === 'Backspace' && !e.target.value && tags.length) {
        tags.pop(); renderTags();
    }
});

document.getElementById('tags-input-wrap').addEventListener('click', () => {
    document.getElementById('tags-input').focus();
});

// ── Load categories ─────────────────────────────────────────
async function loadCategories() {
    try {
        const res = await fetch('/api/categories');
        const cats = await res.json();
        const sel = document.getElementById('category-select');
        sel.innerHTML = '<option value="">No category</option>';
        cats.forEach(c => {
            const opt = document.createElement('option');
            opt.value = c.id;
            opt.textContent = c.name;
            sel.appendChild(opt);
        });
    } catch (err) {
        console.error('Failed to load categories:', err);
    }
}
loadCategories();

// ── Image paste ─────────────────────────────────────────────
document.addEventListener('paste', async (e) => {
    if (!document.querySelector('.ql-editor:focus')) return;
    const items = e.clipboardData?.items;
    if (!items) return;
    for (const item of items) {
        if (item.type.startsWith('image/')) {
            e.preventDefault();
            e.stopPropagation();
            const file = item.getAsFile();
            if (file) await insertImage(file);
            return;
        }
    }
}, true);

async function insertImage(file) {
    if (!quill) return;
    const form = new FormData();
    form.append('file', file);
    form.append('memo_id', '0');
    try {
        const res = await fetch('/api/upload', { method: 'POST', body: form });
        const data = await res.json();
        const range = quill.getSelection(true);
        quill.insertEmbed(range.index, 'image', data.url);
        quill.setSelection(range.index + 1);
    } catch (err) {
        showToast('Upload failed', 'error');
    }
}

// ── Save ────────────────────────────────────────────────────
async function saveMemo() {
    if (!quill) return;
    const content = quill.root.innerHTML;
    const plain = quill.getText().trim();
    if (!plain) { showToast('Empty!', 'error'); return; }

    const title = plain.split('\n')[0].substring(0, 80);
    const catId = document.getElementById('category-select').value || null;

    try {
        const res = await fetch('/api/memos', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                title, content, is_pinned: 0,
                category_id: catId ? parseInt(catId) : null,
                tags: tags.join(',')
            })
        });
        if (res.ok) {
            quill.setText('');
            tags = []; renderTags();
            document.getElementById('category-select').value = '';
            showToast('Saved!', 'success');
        } else {
            showToast('Failed!', 'error');
        }
    } catch (err) {
        showToast('Network error', 'error');
    }
}

// ── Toast ───────────────────────────────────────────────────
function showToast(msg, type) {
    const el = document.getElementById('toast');
    el.textContent = msg;
    el.className = `toast toast-${type}`;
    setTimeout(() => { el.className = 'toast'; el.textContent = ''; }, 2000);
}
