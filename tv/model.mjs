export function localDate(now = new Date()) {
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`;
}

export function showState(show, release, today = localDate()) {
  const seasons = (release?.seasons ?? []).filter(s => s.number > 0).toSorted((a, b) => a.number - b.number);
  const latest = seasons.at(-1)?.number ?? 0;
  const next = seasons.find(s => s.number > show.watchedThrough);
  const season = next?.number ?? show.watchedThrough + 1;
  const premiere = next?.premiereDate ?? null;
  const available = Boolean(premiere && premiere <= today);
  let status = 'waiting';
  if (release?.status === 'Ended' && latest > 0 && show.watchedThrough >= latest) status = 'done';
  else if (show.watching) status = 'watching';
  else if (available) status = 'ready';
  return { status, season, premiere, latest, available, endDate: next?.endDate ?? null };
}

export function validProgress(value) {
  return value && typeof value.watching === 'boolean' && Number.isSafeInteger(value.watchedThrough) && value.watchedThrough >= 0 && value.watchedThrough <= 1000;
}

export function mergedShow(show, saved) {
  return validProgress(saved) ? { ...show, watching: saved.watching, watchedThrough: saved.watchedThrough } : { ...show };
}

export function importedProgress(config, imported) {
  if (!imported || imported.version !== 1 || !Array.isArray(imported.shows) || !imported.shows.length) {
    throw new Error('Choose a watchlist JSON export.');
  }
  const updates = {};
  const known = new Set(config.shows.map(show => show.id));
  const seen = new Set();
  for (const show of imported.shows) {
    if (!show || typeof show.id !== 'string' || seen.has(show.id) || !validProgress(show)) {
      throw new Error('The file contains invalid progress.');
    }
    seen.add(show.id);
    if (known.has(show.id)) updates[show.id] = { watching: show.watching, watchedThrough: show.watchedThrough };
  }
  if (!Object.keys(updates).length) throw new Error('This file has no shows from your watchlist.');
  return updates;
}

export function compareEntries(a, b) {
  const rank = { watching: 0, ready: 1, waiting: 2, done: 3 };
  const groupOrder = rank[a.state.status] - rank[b.state.status];
  if (groupOrder || a.state.status !== 'waiting') return groupOrder;
  if (!a.state.premiere) return b.state.premiere ? 1 : 0;
  if (!b.state.premiere) return -1;
  return a.state.premiere.localeCompare(b.state.premiere);
}
