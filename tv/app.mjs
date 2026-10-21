import { compareEntries, cycleSeason, importedProgress, localDate, mergedShow, seasonBoxes, showState, validProgress } from './model.mjs';

const $ = selector => document.querySelector(selector);
const STORAGE_KEY = 'vibing.tv.progress.v1';
const editableHosts = new Set(['localhost', '127.0.0.1', '[::1]', '::1', '0.0.0.0']);
const canEditProgress = editableHosts.has(location.hostname) || location.hostname.endsWith('.localhost');
const statusNames = { watching: 'Watching', ready: 'Ready to watch', waiting: 'Waiting', done: 'Finished' };
const seasonNames = { done: 'Done', watching: 'Watching', unwatched: 'Not watched' };
const seasonIcons = { done: '✓', watching: '▶', unwatched: '○' };
const nextSeasonStatus = { unwatched: 'watching', watching: 'done', done: 'unwatched' };
let config;
let releases = { shows: {} };
let progress = {};
let tab = 'active';
let filter = 'all';
let editingId;
let toastTimer;
let storageWarning = false;

function element(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function notify(message) {
  clearTimeout(toastTimer);
  $('#toast').textContent = message;
  $('#toast').hidden = false;
  toastTimer = setTimeout(() => { $('#toast').hidden = true; }, 5000);
}

function notice(message) {
  $('#notice').textContent = message;
  $('#notice').hidden = false;
}

function readProgress() {
  if (!canEditProgress) return;
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return;
    const data = JSON.parse(raw);
    if (!data || typeof data !== 'object' || Array.isArray(data)) throw new Error('Invalid progress');
    progress = Object.fromEntries(config.shows.filter(show => validProgress(data[show.id])).map(show => [show.id, data[show.id]]));
  } catch {
    storageWarning = true;
    notice('Saved progress could not be read. Your original list is shown; use Export to keep a backup of new changes.');
  }
}

function persist() {
  if (!canEditProgress) return false;
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(progress));
    storageWarning = false;
    return true;
  } catch {
    storageWarning = true;
    notice('This browser could not save your progress. Your changes work for this visit; use Export to keep them.');
    return false;
  }
}

function dateLabel(value, options = {}) {
  if (!value) return '';
  return new Intl.DateTimeFormat('en-US', { month: 'short', day: 'numeric', year: 'numeric', ...options }).format(new Date(`${value}T12:00:00`));
}

function entries() {
  const today = localDate();
  return config.shows.map(original => {
    const show = mergedShow(original, progress[original.id]);
    const release = releases.shows[show.id];
    return { show, release, state: showState(show, release, today) };
  });
}

function makeRow({ show, release, state }) {
  const row = element('article', `show-row ${state.status}`);
  row.dataset.show = show.id;
  const series = element('div', 'series-cell');
  const title = element('h3', 'show-title');
  if (canEditProgress) {
    const titleButton = element('button', 'show-title-button', show.title);
    titleButton.type = 'button';
    titleButton.addEventListener('click', () => edit(show.id));
    title.append(titleButton);
  } else title.textContent = show.title;
  series.append(title, element('span', 'show-network', [release?.network, release?.status === 'Ended' ? 'Series ended' : null].filter(Boolean).join(' · ') || 'Release details pending'), element('span', 'sr-only', statusNames[state.status]));

  const season = element('div', 'season-cell');
  const boxes = element('div', 'season-boxes');
  boxes.setAttribute('role', 'group');
  boxes.setAttribute('aria-label', `Seasons for ${show.title}`);
  for (const { number, status } of seasonBoxes(show, release)) {
    const box = element(canEditProgress ? 'button' : 'span', `season-box season-${status}`);
    box.dataset.season = number;
    box.dataset.state = status;
    const label = `${show.title}, season ${number}: ${seasonNames[status]}`;
    box.setAttribute('aria-label', canEditProgress ? `${label}. Mark ${seasonNames[nextSeasonStatus[status]].toLowerCase()}.` : label);
    box.title = canEditProgress ? `${label}. Click to mark ${seasonNames[nextSeasonStatus[status]].toLowerCase()}.` : label;
    const icon = element('span', 'season-icon', seasonIcons[status]);
    icon.setAttribute('aria-hidden', 'true');
    box.append(element('span', 'season-number', `S${number}`), icon);
    if (canEditProgress) {
      box.type = 'button';
      box.addEventListener('click', () => toggleSeason(show.id, number));
    }
    boxes.append(box);
  }
  season.append(boxes);

  const date = element('div', 'date-cell');
  if (state.premiere && state.status !== 'done') {
    const value = element('time', '', dateLabel(state.premiere));
    value.dateTime = state.premiere;
    value.setAttribute('aria-label', `Season ${state.season} ${state.available ? 'premiered' : 'premieres'} ${dateLabel(state.premiere)}`);
    date.title = value.getAttribute('aria-label');
    date.append(value);
  } else {
    date.textContent = state.status === 'done' ? 'Finished' : release ? 'Not announced' : 'Unavailable';
    date.title = state.status === 'done' ? 'Every season finished' : release ? `Season ${state.season}: date not announced` : 'Release check unavailable';
  }

  row.append(series, date, season);
  return row;
}

function renderUpcoming(all) {
  const future = all.filter(entry => entry.state.status !== 'done' && entry.state.premiere && !entry.state.available)
    .toSorted((a, b) => a.state.premiere.localeCompare(b.state.premiere)).slice(0, 4);
  const nodes = future.map(({ show, state }) => {
    const item = element('div', 'upcoming-item');
    const tile = element('div', 'date-tile');
    const date = new Date(`${state.premiere}T12:00:00`);
    tile.setAttribute('aria-label', dateLabel(state.premiere));
    tile.append(element('span', '', new Intl.DateTimeFormat('en-US', { month: 'short' }).format(date)), element('strong', '', date.getDate()));
    const detail = element('div');
    detail.append(element('h3', 'upcoming-title', show.title), element('p', 'upcoming-detail', `Season ${state.season} · ${date.getFullYear()}`));
    item.append(tile, detail);
    return item;
  });
  if (!nodes.length) nodes.push(element('p', 'muted', 'No upcoming premiere dates announced yet. A good time to catch up.'));
  $('#upcoming-list').replaceChildren(...nodes);
}

function render() {
  if (!config) return;
  const all = entries();
  const active = all.filter(entry => entry.state.status !== 'done');
  const done = all.filter(entry => entry.state.status === 'done');
  const counts = { watching: 0, ready: 0, waiting: 0 };
  active.forEach(entry => counts[entry.state.status]++);
  $('#active-count').textContent = active.length;
  $('#done-count').textContent = done.length;
  $('#all-count').textContent = active.length;
  for (const [status, count] of Object.entries(counts)) $(`#${status}-count`).textContent = count;
  $('#filters').hidden = tab === 'done';
  $('#collection-panel').setAttribute('aria-labelledby', `${tab}-tab`);
  document.querySelectorAll('[data-tab]').forEach(button => {
    const selected = button.dataset.tab === tab;
    button.classList.toggle('selected', selected);
    button.setAttribute('aria-selected', String(selected));
    button.tabIndex = selected ? 0 : -1;
  });
  document.querySelectorAll('[data-filter]').forEach(button => {
    const selected = button.dataset.filter === filter;
    button.classList.toggle('selected', selected);
    button.setAttribute('aria-pressed', String(selected));
  });
  const query = $('#search').value.trim().toLocaleLowerCase();
  const visible = (tab === 'done' ? done : active)
    .filter(entry => (tab === 'done' || filter === 'all' || entry.state.status === filter) && `${entry.show.title} ${entry.release?.network ?? ''} ${entry.show.note ?? ''}`.toLocaleLowerCase().includes(query))
    .toSorted(compareEntries);
  if (visible.length) $('#show-list').replaceChildren(...visible.map(makeRow));
  else {
    const empty = element('div', 'empty-state');
    const noDone = tab === 'done' && !done.length && !query;
    empty.append(element('strong', '', noDone ? 'The story’s still going.' : 'Nothing on this channel.'), document.createTextNode(noDone ? 'Finish every season of an ended show and it will land here.' : 'Try another search or filter.'));
    $('#show-list').replaceChildren(empty);
  }
  $('#show-list').setAttribute('aria-busy', 'false');
  $('#list-summary').textContent = `${visible.length} show${visible.length === 1 ? '' : 's'} ${tab === 'done' ? 'finished' : 'in the mix'}${query ? ` matching “${$('#search').value.trim()}”` : ''}.`;
  renderUpcoming(all);
}

function setTab(value) {
  tab = value;
  filter = 'all';
  render();
}

function updateProgress(id, value) {
  if (!canEditProgress || !config || !validProgress(value) || !config.shows.some(show => show.id === id)) return false;
  progress[id] = value;
  const saved = persist();
  render();
  $('#progress-status').textContent = 'Local changes · Save to repository to publish';
  return saved;
}

function toggleSeason(id, number) {
  if (!canEditProgress || !config) return;
  const entry = entries().find(entry => entry.show.id === id);
  if (!entry) return;
  const value = cycleSeason(entry.show, entry.release, number);
  const saved = updateProgress(id, value);
  // Re-rendering may reorder the show or move it to Done. Keep keyboard focus useful.
  const row = [...document.querySelectorAll('.show-row')].find(row => row.dataset.show === id);
  const button = row && ([...row.querySelectorAll('.season-box')].find(box => Number(box.dataset.season) === number) ?? row.querySelector('.season-box'));
  (button ?? $(`#${tab}-tab`)).focus({ preventScroll: true });
  const status = value.watching ? 'watching' : value.watchedThrough >= number ? 'done' : 'unwatched';
  notify(`${entry.show.title} · S${number}: ${seasonNames[status]}.${saved ? '' : ' Save to repository or Export to keep your progress.'}`);
}

function edit(id) {
  if (!canEditProgress || !config) return;
  editingId = id;
  const { show, release, state } = entries().find(entry => entry.show.id === id);
  $('#dialog-title').textContent = show.title;
  $('#dialog-meta').textContent = [release?.network, release?.status === 'Ended' ? 'Series ended' : null].filter(Boolean).join(' · ');
  $('#dialog-note').textContent = show.note ?? '';
  $('#dialog-note').hidden = !show.note;
  const airedSeasons = (release?.seasons ?? []).filter(s => s.number <= (show.seasonLimit ?? Infinity) && s.premiereDate && s.premiereDate <= localDate());
  // Include already-recorded progress even if an upstream date is temporarily missing.
  const maxSeason = Math.min(show.seasonLimit ?? Infinity, Math.max(show.watchedThrough, ...airedSeasons.map(s => s.number), 0));
  const options = [new Option('None yet', '0')];
  for (let number = 1; number <= maxSeason; number++) options.push(new Option(`Season ${number}`, String(number)));
  $('#watched-through').replaceChildren(...options);
  $('#watched-through').value = String(show.watchedThrough);
  $('#currently-watching').checked = show.watching && state.status !== 'done';
  let source;
  try {
    const url = new URL(release?.url);
    if (url.protocol === 'https:' && url.hostname === 'www.tvmaze.com') source = url.href;
  } catch { /* No source available yet. */ }
  $('#show-source').hidden = !source;
  if (source) $('#show-source').href = source;
  $('#progress-dialog').showModal();
}

$('#watched-through').addEventListener('change', () => {
  // Finishing a season stops watching until the viewer explicitly starts another.
  $('#currently-watching').checked = false;
});

$('#progress-form').addEventListener('submit', event => {
  event.preventDefault();
  if (!canEditProgress || !config || !editingId) return;
  const value = { watchedThrough: Number($('#watched-through').value), watching: $('#currently-watching').checked };
  if (!validProgress(value)) return;
  const saved = updateProgress(editingId, value);
  const entry = config.shows.find(show => show.id === editingId);
  const state = showState(mergedShow(entry, progress[editingId]), releases.shows[editingId]);
  $('#progress-dialog').close();
  notify(saved ? (state.status === 'done' ? `${entry.title} moved to Done. That’s a wrap.` : 'Progress saved in this browser. Save to repository when ready.') : 'Progress updated for this visit. Save to repository or Export to keep it.');
});
$('#close-dialog').addEventListener('click', () => $('#progress-dialog').close());
$('#progress-dialog').addEventListener('click', event => {
  if (event.target === $('#progress-dialog')) {
    const bounds = event.target.getBoundingClientRect();
    if (event.clientX < bounds.left || event.clientX > bounds.right || event.clientY < bounds.top || event.clientY > bounds.bottom) event.target.close();
  }
});
document.querySelectorAll('[data-tab]').forEach(button => button.addEventListener('click', () => setTab(button.dataset.tab)));
$('.tabs').addEventListener('keydown', event => {
  if (['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) {
    event.preventDefault();
    setTab(event.key === 'Home' ? 'active' : event.key === 'End' ? 'done' : tab === 'active' ? 'done' : 'active');
    $(`#${tab}-tab`).focus();
  }
});
document.querySelectorAll('[data-filter]').forEach(button => button.addEventListener('click', () => { filter = button.dataset.filter; render(); }));
$('#search').addEventListener('input', () => { if (config) render(); });
$('#view-done').addEventListener('click', () => { if (config) { setTab('done'); $('#done-tab').focus(); } });

function watchlistData() {
  return { ...config, shows: config.shows.map(show => mergedShow(show, progress[show.id])) };
}

function downloadWatchlist(data) {
  const url = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2) + '\n'], { type: 'application/json' }));
  const link = element('a');
  link.href = url;
  link.download = 'shows.json';
  document.body.append(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

$('#export').addEventListener('click', () => {
  if (!config) return;
  downloadWatchlist(watchlistData());
  notify('Exported your list and progress. Keep it for backup or import it on another device.');
});

$('#save-repository').addEventListener('click', async () => {
  if (!canEditProgress || !config) return;
  const data = watchlistData();
  $('#save-repository').disabled = true;
  $('#progress-status').textContent = 'Saving to repository…';
  try {
    const response = await fetch('api/progress', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    // A static preview server has no save endpoint. Preserve edits as a download.
    if (response.status === 404 || response.status === 405 || response.status === 501) {
      throw new TypeError('Local save server unavailable.');
    }
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || 'Could not save progress.');
    $('#progress-status').textContent = JSON.stringify(watchlistData()) === JSON.stringify(data)
      ? 'Saved to repository · ready to commit'
      : 'New local changes · Save to repository again';
    notify(result.message);
  } catch (error) {
    if (error instanceof TypeError || error instanceof SyntaxError) {
      downloadWatchlist(data);
      $('#progress-status').textContent = 'JSON downloaded · apply it with the import script';
      notify('Local save server unavailable. Downloaded shows.json; apply it with scripts/import-progress.mjs.');
    } else {
      $('#progress-status').textContent = 'Save failed · local progress kept';
      notify(`Could not save to repository. ${error.message}`);
    }
  } finally {
    $('#save-repository').disabled = false;
  }
});

$('#import').addEventListener('click', () => { if (canEditProgress && config) $('#import-file').click(); });
$('#import-file').addEventListener('change', async event => {
  if (!canEditProgress || !config) return;
  const file = event.target.files[0];
  if (!file) return;
  try {
    if (file.size > 1_000_000) throw new Error('File is too large.');
    const imported = JSON.parse(await file.text());
    const updates = importedProgress(config, imported);
    progress = { ...progress, ...updates };
    const saved = persist();
    render();
    $('#progress-status').textContent = 'Local changes · Save to repository to publish';
    notify(saved ? `Imported progress for ${Object.keys(updates).length} shows.` : 'Progress imported for this visit. Export to keep it.');
  } catch (error) {
    notify(`Could not import. ${error instanceof SyntaxError ? 'Choose a valid JSON export.' : error.message}`);
  } finally {
    event.target.value = '';
  }
});

window.addEventListener('storage', event => {
  if (canEditProgress && config && (event.key === STORAGE_KEY || event.key === null)) {
    progress = {};
    readProgress();
    render();
    $('#progress-status').textContent = 'Local progress · Save to repository when ready';
  }
});
document.addEventListener('visibilitychange', () => { if (config && !document.hidden) render(); });
setInterval(() => { if (config && !document.hidden) render(); }, 60_000);

async function loadJson(path) {
  const response = await fetch(path, { cache: 'no-cache' });
  if (!response.ok) throw new Error(`${path} returned ${response.status}`);
  return response.json();
}

async function init() {
  const [listResult, releaseResult] = await Promise.allSettled([loadJson('shows.json'), loadJson('releases.json')]);
  if (listResult.status === 'rejected') {
    $('#show-list').textContent = 'The watchlist could not load. Please reload the page.';
    $('#show-list').setAttribute('aria-busy', 'false');
    $('#last-checked').textContent = 'Unable to load';
    $('#upcoming-list').textContent = 'Calendar unavailable.';
    notice(location.protocol === 'file:' ? 'Preview this site with the local server: node scripts/dev-server.mjs, then open http://localhost:8766/.' : 'The show list is unavailable. Check your connection and try again.');
    return;
  }
  config = listResult.value;
  if (releaseResult.status === 'fulfilled') releases = releaseResult.value;
  else notice('Release dates could not load. Your progress is still available; please reload to try again.');
  readProgress();
  if (releases.checkedAt) {
    const checked = new Date(releases.checkedAt);
    $('#last-checked').textContent = `Last checked ${new Intl.DateTimeFormat('en-US', { month: 'short', day: 'numeric', year: 'numeric' }).format(checked)}`;
    if (Date.now() - checked.getTime() > 14 * 24 * 60 * 60 * 1000) notice('Release dates haven’t been checked in over two weeks. The last known dates are shown.');
  } else $('#last-checked').textContent = 'Waiting for the first check';
  if (releases.errors?.length && !storageWarning) notice(`${releases.errors.length} show(s) could not be checked in the latest update. Their last known dates are shown.`);
  render();
  $('#export').disabled = false;
  if (canEditProgress) {
    $('#local-tools').hidden = false;
    $('#import').disabled = false;
    $('#import-file').disabled = false;
    $('#save-repository').disabled = false;
    $('#progress-form').querySelectorAll('input, select, button[type="submit"]').forEach(input => { input.disabled = false; });
    $('#progress-status').textContent = 'Local progress · Save to repository when ready';
  }
}

init().catch(error => {
  console.error(error);
  notice('Something interrupted the watchlist. Please reload the page to try again.');
  $('#show-list').setAttribute('aria-busy', 'false');
});
