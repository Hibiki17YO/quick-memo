// Shared catalog of Quill toolbar options used by both the editor and
// the management settings page.

window.TOOLBAR_CATALOG = [
    { key: 'bold',         label: 'Bold (加粗)',         quill: 'bold' },
    { key: 'italic',       label: 'Italic (斜体)',       quill: 'italic' },
    { key: 'underline',    label: 'Underline (下划线)',  quill: 'underline' },
    { key: 'strike',       label: 'Strikethrough (删除线)', quill: 'strike' },
    { key: 'header',       label: 'Headings (标题)',     quill: { header: [1, 2, 3, false] } },
    { key: 'list-ordered', label: 'Ordered list (有序列表)',   quill: { list: 'ordered' } },
    { key: 'list-bullet',  label: 'Bullet list (无序列表)',    quill: { list: 'bullet' } },
    { key: 'blockquote',   label: 'Blockquote (引用)',   quill: 'blockquote' },
    { key: 'code-block',   label: 'Code block (代码块)', quill: 'code-block' },
    { key: 'image',        label: 'Image (图片)',        quill: 'image' },
    { key: 'clean',        label: 'Clear formatting (清除格式)', quill: 'clean' },
];

window.TOOLBAR_DEFAULT = window.TOOLBAR_CATALOG.map(o => o.key);

// Build Quill toolbar config from a list of enabled keys.
window.buildQuillToolbar = function (enabledKeys) {
    const enabled = new Set(enabledKeys && enabledKeys.length ? enabledKeys : window.TOOLBAR_DEFAULT);
    // Group: inline formatting / headers / lists / blocks / image+clean
    const groups = {
        inline: ['bold', 'italic', 'underline', 'strike'],
        header: ['header'],
        list: ['list-ordered', 'list-bullet'],
        block: ['blockquote', 'code-block'],
        misc: ['image', 'clean'],
    };
    const catalog = Object.fromEntries(window.TOOLBAR_CATALOG.map(o => [o.key, o.quill]));
    const toolbar = [];
    for (const groupKeys of Object.values(groups)) {
        const items = groupKeys.filter(k => enabled.has(k)).map(k => catalog[k]);
        if (items.length) toolbar.push(items);
    }
    return toolbar;
};
