import { highlightCode } from './array-box/src/syntax.js';

const STORAGE_KEY = 'apl-dojo-tierlist';

const LANG_LOGOS = {
    apl:     'array-box/assets/apl.png',
    bqn:     'array-box/assets/bqn.svg',
    j:       'array-box/assets/j_logo.svg',
    uiua:    'array-box/assets/uiua.png',
    kap:     'array-box/assets/kap.png',
    tinyapl: 'array-box/assets/tinyapl.svg',
};

const LANG_FONT_CLASS = {
    apl: 'font-apl', bqn: 'font-bqn', j: 'font-j',
    uiua: 'font-uiua', kap: 'font-kap', tinyapl: 'font-tinyapl',
};

// ── State ──────────────────────────────────────────────

let items = [];
let draggedId = null;
let editingId = null;

async function load() {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) {
        try { items = JSON.parse(raw); return; } catch { /* fall through */ }
    }
    await loadDefaults();
}

async function loadDefaults() {
    try {
        const resp = await fetch('data.json');
        if (resp.ok) items = await resp.json();
    } catch { /* no defaults, start empty */ }
}

function save() {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(items));
}

function nextId() {
    return 'item-' + Date.now() + '-' + Math.random().toString(36).slice(2, 7);
}

// ── Rendering ──────────────────────────────────────────

const ALL_RANKS = ['0', '1', '2', '3+', 'N'];

function rankBadgeText(ranks) {
    if (!ranks || ranks.length === 0) return '';
    if (ranks.length === ALL_RANKS.length) return 'all';
    if (ranks.length === 1) return ranks[0];

    const nums = [];
    let hasN = false;
    for (const r of ALL_RANKS) {
        if (ranks.includes(r)) {
            if (r === 'N') hasN = true;
            else nums.push(r);
        }
    }
    let label = '';
    if (nums.length > 1) label = nums[0] + '-' + nums[nums.length - 1];
    else if (nums.length === 1) label = nums[0];
    if (hasN) label = label ? label + ',N' : 'N';
    return label;
}

function chipFontSize(text, type) {
    const len = text.length;
    if (type === 'primitive') {
        if (len <= 1) return '1.8rem';
        if (len <= 2) return '1.5rem';
        if (len <= 4) return '1.1rem';
        return '0.85rem';
    }
    if (len <= 3) return '1.1rem';
    if (len <= 6) return '0.85rem';
    if (len <= 12) return '0.7rem';
    return '0.6rem';
}

function renderChip(item) {
    const el = document.createElement('div');
    el.className = 'chip';
    el.dataset.id = item.id;
    el.draggable = true;

    const fontSize = chipFontSize(item.text, item.type);

    if (item.type === 'primitive') {
        el.classList.add('chip-primitive', `subtype-${item.subType}`);
        const fontCls = item.highlightLang ? LANG_FONT_CLASS[item.highlightLang] : '';
        el.innerHTML = `<span class="chip-text ${fontCls}" style="font-size:${fontSize}">${escapeHtml(item.text)}</span>`;
    } else if (item.type === 'expression') {
        el.classList.add('chip-expression');
        if (item.subType) el.classList.add(`subtype-${item.subType}`);
        const lang = item.highlightLang || '';
        const fontCls = lang ? LANG_FONT_CLASS[lang] : '';
        const highlighted = lang ? highlightCode(item.text, lang) : escapeHtml(item.text);
        el.innerHTML = `<span class="chip-text ${fontCls}" style="font-size:${fontSize}">${highlighted}</span>`;
    } else {
        el.classList.add('chip-concept');
        el.innerHTML = `<span class="chip-text" style="font-size:${fontSize}">${escapeHtml(item.text)}</span>`;
    }

    if (item.name) {
        const wrap = document.createElement('div');
        wrap.className = 'chip-tooltip-wrap';
        const tooltip = document.createElement('span');
        tooltip.className = 'chip-tooltip';
        tooltip.textContent = item.name;
        const leader = document.createElement('div');
        leader.className = 'chip-tooltip-leader';
        wrap.appendChild(tooltip);
        wrap.appendChild(leader);
        el.appendChild(wrap);
    }

    if (item.ranks && item.ranks.length > 0) {
        const badge = document.createElement('span');
        badge.className = 'chip-rank-badge';
        badge.textContent = rankBadgeText(item.ranks);
        el.appendChild(badge);
    }

    if (item.languages && item.languages.length > 0) {
        const langsDiv = document.createElement('div');
        langsDiv.className = 'chip-langs';
        for (const lang of item.languages) {
            const img = document.createElement('img');
            img.src = LANG_LOGOS[lang];
            img.alt = lang;
            img.className = 'chip-lang-logo';
            langsDiv.appendChild(img);
        }
        el.appendChild(langsDiv);
    }

    const del = document.createElement('button');
    del.className = 'chip-delete';
    del.textContent = '×';
    del.addEventListener('click', (e) => {
        e.stopPropagation();
        items = items.filter(it => it.id !== item.id);
        save();
        renderAll();
    });
    el.appendChild(del);

    el.addEventListener('dragstart', onDragStart);
    el.addEventListener('dragend', onDragEnd);
    el.addEventListener('click', () => editItem(item.id));

    return el;
}

function editItem(id) {
    const item = items.find(it => it.id === id);
    if (!item) return;

    editingId = id;
    const form = document.getElementById('creation-form');
    form.hidden = false;

    document.querySelector(`input[name="item-type"][value="${item.type}"]`).checked = true;
    if (item.subType) {
        const subRadio = document.querySelector(`input[name="item-subtype"][value="${item.subType}"]`);
        if (subRadio) subRadio.checked = true;
    }
    document.getElementById('item-text').value = item.text;
    document.getElementById('item-name').value = item.name || '';
    if (item.highlightLang) {
        document.getElementById('lang-expr').value = item.highlightLang;
    }

    document.querySelectorAll('#lang-checkboxes input[type="checkbox"]').forEach(cb => {
        cb.checked = item.languages && item.languages.includes(cb.value);
    });

    document.querySelectorAll('#rank-checkboxes input[type="checkbox"]').forEach(cb => {
        cb.checked = item.ranks && item.ranks.includes(cb.value);
    });

    const showSubtype = item.type === 'primitive' || item.type === 'expression';
    const isFn = item.subType === 'monadic-function' || item.subType === 'dyadic-function';
    document.getElementById('subtype-group').style.display = showSubtype ? '' : 'none';
    document.getElementById('lang-group').style.display = item.type === 'expression' ? '' : 'none';
    document.getElementById('rank-group').style.display = (showSubtype && isFn) ? '' : 'none';
    document.getElementById('name-group').style.display = item.type === 'primitive' ? '' : 'none';

    const btn = document.getElementById('btn-create');
    btn.textContent = 'Update';
    document.getElementById('item-text').focus();
}

function renderAll() {
    document.querySelectorAll('.tier-dropzone').forEach(zone => {
        zone.innerHTML = '';
    });
    document.getElementById('staging-items').innerHTML = '';

    for (const item of items) {
        const chip = renderChip(item);
        if (item.tierId) {
            const zone = document.querySelector(`.tier-dropzone[data-tier="${item.tierId}"]`);
            if (zone) zone.appendChild(chip);
        } else {
            document.getElementById('staging-items').appendChild(chip);
        }
    }
}

function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

// ── Drag & Drop ────────────────────────────────────────

function onDragStart(e) {
    draggedId = e.currentTarget.dataset.id;
    e.currentTarget.classList.add('dragging');
    e.dataTransfer.effectAllowed = 'move';
    e.dataTransfer.setData('text/plain', draggedId);
}

function onDragEnd(e) {
    e.currentTarget.classList.remove('dragging');
    draggedId = null;
    document.querySelectorAll('.drag-over').forEach(el => el.classList.remove('drag-over'));
}

function onDragOver(e) {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
    e.currentTarget.classList.add('drag-over');
}

function onDragLeave(e) {
    e.currentTarget.classList.remove('drag-over');
}

function onDropTier(e) {
    e.preventDefault();
    e.currentTarget.classList.remove('drag-over');
    const id = e.dataTransfer.getData('text/plain');
    const tier = e.currentTarget.dataset.tier;
    const item = items.find(it => it.id === id);
    if (item) {
        item.tierId = tier;
        save();
        renderAll();
    }
}

function onDropStaging(e) {
    e.preventDefault();
    e.currentTarget.classList.remove('drag-over');
    const id = e.dataTransfer.getData('text/plain');
    const item = items.find(it => it.id === id);
    if (item) {
        item.tierId = null;
        save();
        renderAll();
    }
}

function setupDropZones() {
    document.querySelectorAll('.tier-dropzone').forEach(zone => {
        zone.addEventListener('dragover', onDragOver);
        zone.addEventListener('dragleave', onDragLeave);
        zone.addEventListener('drop', onDropTier);
    });

    const staging = document.getElementById('staging-items');
    staging.addEventListener('dragover', onDragOver);
    staging.addEventListener('dragleave', onDragLeave);
    staging.addEventListener('drop', onDropStaging);
}

// ── Creation Form ──────────────────────────────────────

function setupForm() {
    const btnAdd = document.getElementById('btn-add');
    const form = document.getElementById('creation-form');
    const subtypeGroup = document.getElementById('subtype-group');
    const langGroup = document.getElementById('lang-group');
    const typeRadios = document.querySelectorAll('input[name="item-type"]');
    const btnCreate = document.getElementById('btn-create');
    const textInput = document.getElementById('item-text');

    btnAdd.addEventListener('click', () => {
        if (editingId) {
            editingId = null;
            document.getElementById('btn-create').textContent = 'Create';
            textInput.value = '';
        }
        form.hidden = !form.hidden;
        if (!form.hidden) textInput.focus();
    });

    const rankGroup = document.getElementById('rank-group');
    const subtypeRadios = document.querySelectorAll('input[name="item-subtype"]');

    function isFunction(subType) {
        return subType === 'monadic-function' || subType === 'dyadic-function';
    }

    const nameGroup = document.getElementById('name-group');

    function updateFormVisibility() {
        const type = document.querySelector('input[name="item-type"]:checked').value;
        const showSubtype = type === 'primitive' || type === 'expression';
        subtypeGroup.style.display = showSubtype ? '' : 'none';
        langGroup.style.display = type === 'expression' ? '' : 'none';
        nameGroup.style.display = type === 'primitive' ? '' : 'none';

        if (showSubtype) {
            const sub = document.querySelector('input[name="item-subtype"]:checked').value;
            rankGroup.style.display = isFunction(sub) ? '' : 'none';
        } else {
            rankGroup.style.display = 'none';
        }
    }

    typeRadios.forEach(r => r.addEventListener('change', updateFormVisibility));
    subtypeRadios.forEach(r => r.addEventListener('change', updateFormVisibility));
    updateFormVisibility();

    btnCreate.addEventListener('click', createItem);
    textInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') createItem();
    });

    document.getElementById('btn-lang-all').addEventListener('click', () => {
        document.querySelectorAll('#lang-checkboxes input[type="checkbox"]').forEach(cb => cb.checked = true);
    });
    document.getElementById('btn-lang-none').addEventListener('click', () => {
        document.querySelectorAll('#lang-checkboxes input[type="checkbox"]').forEach(cb => cb.checked = false);
    });
    document.getElementById('btn-rank-all').addEventListener('click', () => {
        document.querySelectorAll('#rank-checkboxes input[type="checkbox"]').forEach(cb => cb.checked = true);
    });
    document.getElementById('btn-rank-none').addEventListener('click', () => {
        document.querySelectorAll('#rank-checkboxes input[type="checkbox"]').forEach(cb => cb.checked = false);
    });
}

function createItem() {
    const text = document.getElementById('item-text').value.trim();
    if (!text) return;

    const type = document.querySelector('input[name="item-type"]:checked').value;
    const subType = (type === 'primitive' || type === 'expression')
        ? document.querySelector('input[name="item-subtype"]:checked').value
        : null;

    const name = type === 'primitive'
        ? document.getElementById('item-name').value.trim() || null
        : null;

    const highlightLang = type === 'expression'
        ? document.getElementById('lang-expr').value || null
        : null;

    const languages = [];
    document.querySelectorAll('#lang-checkboxes input[type="checkbox"]:checked').forEach(cb => {
        languages.push(cb.value);
    });

    const isFn = subType === 'monadic-function' || subType === 'dyadic-function';
    const ranks = [];
    if (isFn) {
        document.querySelectorAll('#rank-checkboxes input[type="checkbox"]:checked').forEach(cb => {
            ranks.push(cb.value);
        });
    }

    if (editingId) {
        const existing = items.find(it => it.id === editingId);
        if (existing) {
            existing.type = type;
            existing.subType = subType;
            existing.text = text;
            existing.name = name;
            existing.highlightLang = highlightLang;
            existing.languages = languages;
            existing.ranks = ranks;
        }
        editingId = null;
        document.getElementById('btn-create').textContent = 'Create';
    } else {
        items.push({
            id: nextId(),
            type,
            subType,
            text,
            name,
            highlightLang,
            languages,
            ranks,
            tierId: null,
        });
    }

    save();
    renderAll();

    document.getElementById('item-text').value = '';
    document.getElementById('item-name').value = '';
    document.getElementById('item-text').focus();
}

// ── Color Mode ─────────────────────────────────────────

function setupLegend() {
    const rows = document.querySelectorAll('.legend-row');
    const app = document.querySelector('.app');

    const saved = localStorage.getItem('apl-dojo-colormode') || '4color';
    applyMode(saved);

    rows.forEach(row => {
        row.addEventListener('click', () => {
            applyMode(row.dataset.mode);
        });
    });

    function applyMode(mode) {
        rows.forEach(r => r.classList.toggle('legend-row-active', r.dataset.mode === mode));
        app.classList.remove('mode-4color', 'mode-3color');
        app.classList.add(`mode-${mode}`);
        localStorage.setItem('apl-dojo-colormode', mode);
    }

    sizeFunctionChip();
    window.addEventListener('resize', sizeFunctionChip);
}

function sizeFunctionChip() {
    const row4 = document.getElementById('legend-4color');
    const chips4 = row4.querySelectorAll('.legend-chip');
    if (chips4.length < 2) return;
    const w1 = chips4[0].offsetWidth;
    const w2 = chips4[1].offsetWidth;
    const gap = 6;
    const wide = document.querySelector('.legend-chip-wide');
    if (wide) wide.style.width = (w1 + w2 + gap) + 'px';
}

// ── Export / Reset ──────────────────────────────────────

function setupHeaderActions() {
    document.getElementById('btn-export').addEventListener('click', () => {
        const json = JSON.stringify(items, null, 2);
        const blob = new Blob([json], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'data.json';
        a.click();
        URL.revokeObjectURL(url);
    });

    document.getElementById('btn-reset').addEventListener('click', async () => {
        localStorage.removeItem(STORAGE_KEY);
        items = [];
        await loadDefaults();
        renderAll();
    });
}

// ── Init ───────────────────────────────────────────────

async function init() {
    await load();
    setupDropZones();
    setupForm();
    setupLegend();
    setupHeaderActions();
    renderAll();
}

init();
