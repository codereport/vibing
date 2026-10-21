export function localDate(now = new Date()) {
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`;
}

function listedSeasons(show, release) {
  return (release?.seasons ?? []).filter(season => season.number > 0 && season.number <= (show.seasonLimit ?? Infinity));
}

export function showState(show, release, today = localDate()) {
  const seasons = listedSeasons(show, release).toSorted((a, b) => a.number - b.number);
  const latest = seasons.at(-1)?.number ?? 0;
  const next = seasons.find(s => s.number > show.watchedThrough);
  const season = next?.number ?? show.watchedThrough + 1;
  const premiere = next?.premiereDate ?? null;
  const available = Boolean(premiere && premiere <= today);
  let status = 'waiting';
  if (release?.status === 'Ended' && latest > 0 && show.watchedThrough >= latest) status = 'done';
  else if (show.watching && season <= (show.seasonLimit ?? Infinity)) status = 'watching';
  else if (available) status = 'ready';
  return { status, season, premiere, latest, available, endDate: next?.endDate ?? null };
}

export function validProgress(value) {
  return value && typeof value.watching === 'boolean' && Number.isSafeInteger(value.watchedThrough) && value.watchedThrough >= 0 && value.watchedThrough <= 1000;
}

export function mergedShow(show, saved) {
  return validProgress(saved) ? { ...show, watching: saved.watching, watchedThrough: saved.watchedThrough } : { ...show };
}

export function seasonBoxes(show, release) {
  const known = listedSeasons(show, release).map(season => season.number).filter(number => Number.isSafeInteger(number) && number <= 1000);
  const state = showState(show, release);
  const watching = state.status === 'watching' ? state.season : null;
  // Keep recorded progress visible even if a release check temporarily omits it.
  const total = Math.min(show.seasonLimit ?? Infinity, Math.max(...known, show.watchedThrough, watching ?? 0, known.length ? 0 : 5));
  const first = show.watchedThrough > 0 ? Math.max(1, total - 4) : 1;
  return Array.from({ length: Math.min(5, total - first + 1) }, (_, index) => {
    const number = first + index;
    const status = number <= show.watchedThrough ? 'done' : number === watching ? 'watching' : 'unwatched';
    return { number, status };
  });
}

export function cycleSeason(show, release, number) {
  const season = seasonBoxes(show, release).find(season => season.number === number);
  if (!season) throw new Error('Choose a visible season.');
  // Progress is a completed prefix with at most one season being watched.
  return {
    watchedThrough: season.status === 'watching' ? number : number - 1,
    watching: season.status === 'unwatched',
  };
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
