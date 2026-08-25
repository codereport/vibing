const BOOKS = [
  {
    id: "three-body-problem",
    title: "The Three-Body Problem",
    author: "Cixin Liu",
    readDate: "2024-04-19",
    series: "remembrance",
    seriesOrder: 1,
    cover: "id:9157544",
    work: "OL17267881W",
    accent: "#785b3f",
  },
  {
    id: "dark-forest",
    title: "The Dark Forest",
    author: "Cixin Liu",
    readDate: "2024-04-26",
    series: "remembrance",
    seriesOrder: 2,
    cover: "id:10526598",
    work: "OL16314245W",
    accent: "#38623e",
  },
  {
    id: "deaths-end",
    title: "Death’s End",
    author: "Cixin Liu",
    readDate: "2024-06-22",
    series: "remembrance",
    seriesOrder: 3,
    cover: "id:7893958",
    work: "OL17610507W",
    accent: "#405a73",
  },
  {
    id: "redemption-of-time",
    title: "The Redemption of Time",
    author: "Baoshu",
    readDate: "2024-10-21",
    series: "remembrance",
    seriesOrder: 4,
    orderLabel: "Coda",
    countsTowardAverage: false,
    cover: "id:10158478",
    work: "OL20847868W",
    accent: "#56457b",
  },
  {
    id: "children-of-time",
    title: "Children of Time",
    author: "Adrian Tchaikovsky",
    readDate: "2024-06-25",
    series: "children-time",
    seriesOrder: 1,
    cover: "id:8264706",
    work: "OL17373843W",
    accent: "#51764d",
  },
  {
    id: "children-of-ruin",
    title: "Children of Ruin",
    author: "Adrian Tchaikovsky",
    readDate: null,
    series: "children-time",
    seriesOrder: 2,
    cover: "id:8750923",
    work: "OL20079532W",
    accent: "#7d4938",
  },
  {
    id: "children-of-memory",
    title: "Children of Memory",
    author: "Adrian Tchaikovsky",
    readDate: null,
    series: "children-time",
    seriesOrder: 3,
    cover: "id:14633285",
    work: "OL28018696W",
    accent: "#9a7034",
  },
  {
    id: "children-of-strife",
    title: "Children of Strife",
    author: "Adrian Tchaikovsky",
    readDate: null,
    series: "children-time",
    seriesOrder: 4,
    cover: "isbn:9781035057788",
    accent: "#40756e",
  },
  {
    id: "memory-called-empire",
    title: "A Memory Called Empire",
    author: "Arkady Martine",
    readDate: "2024-08-18",
    series: "teixcalaan",
    seriesOrder: 1,
    cover: "id:8802134",
    work: "OL20157046W",
    accent: "#816d43",
  },
  {
    id: "desolation-called-peace",
    title: "A Desolation Called Peace",
    author: "Arkady Martine",
    readDate: null,
    series: "teixcalaan",
    seriesOrder: 2,
    cover: "id:10718806",
    work: "OL20832939W",
    accent: "#865040",
  },
  {
    id: "we-are-legion",
    title: "We Are Legion (We Are Bob)",
    author: "Dennis E. Taylor",
    readDate: "2024-08-21",
    series: "bobiverse",
    seriesOrder: 1,
    cover: "olid:OL26770283M",
    accent: "#365f7d",
  },
  {
    id: "for-we-are-many",
    title: "For We Are Many",
    author: "Dennis E. Taylor",
    readDate: "2024-08-26",
    series: "bobiverse",
    seriesOrder: 2,
    cover: "id:11329842",
    work: "OL19742648W",
    accent: "#63458b",
  },
  {
    id: "all-these-worlds",
    title: "All These Worlds",
    author: "Dennis E. Taylor",
    readDate: "2024-08-30",
    series: "bobiverse",
    seriesOrder: 3,
    cover: "id:12750210",
    work: "OL19742647W",
    accent: "#8a5b3e",
  },
  {
    id: "heavens-river",
    title: "Heaven’s River",
    author: "Dennis E. Taylor",
    readDate: "2024-09-24",
    series: "bobiverse",
    seriesOrder: 4,
    cover: "id:10522898",
    work: "OL23705087W",
    accent: "#416783",
  },
  {
    id: "not-till-lost",
    title: "Not Till We Are Lost",
    author: "Dennis E. Taylor",
    readDate: "2024-10-01",
    series: "bobiverse",
    seriesOrder: 5,
    cover: "id:14820348",
    work: "OL40592593W",
    accent: "#567b65",
  },
  {
    id: "ready-player-one",
    title: "Ready Player One",
    author: "Ernest Cline",
    readDate: "2024-10-04",
    series: "ready-player",
    seriesOrder: 1,
    cover: "id:8737626",
    work: "OL15936512W",
    accent: "#8b6538",
  },
  {
    id: "ready-player-two",
    title: "Ready Player Two",
    author: "Ernest Cline",
    readDate: "2024-10-08",
    series: "ready-player",
    seriesOrder: 2,
    cover: "id:10250001",
    work: "OL20907281W",
    accent: "#467b7f",
  },
  {
    id: "altered-carbon",
    title: "Altered Carbon",
    author: "Richard K. Morgan",
    readDate: "2024-10-13",
    series: "kovacs",
    seriesOrder: 1,
    cover: "id:9335989",
    work: "OL20668162W",
    accent: "#973f44",
  },
  {
    id: "broken-angels",
    title: "Broken Angels",
    author: "Richard K. Morgan",
    readDate: null,
    series: "kovacs",
    seriesOrder: 2,
    cover: "id:210814",
    work: "OL5730139W",
    accent: "#785b49",
  },
  {
    id: "woken-furies",
    title: "Woken Furies",
    author: "Richard K. Morgan",
    readDate: null,
    series: "kovacs",
    seriesOrder: 3,
    cover: "id:211838",
    work: "OL5730142W",
    accent: "#636b69",
  },
  {
    id: "neuromancer",
    title: "Neuromancer",
    author: "William Gibson",
    readDate: null,
    series: "sprawl",
    seriesOrder: 1,
    cover: "isbn:9781473217386",
    work: "OL27258W",
    accent: "#c52e88",
  },
  {
    id: "count-zero",
    title: "Count Zero",
    author: "William Gibson",
    readDate: null,
    series: "sprawl",
    seriesOrder: 2,
    cover: "isbn:9781473217409",
    work: "OL27256W",
    accent: "#249d68",
  },
  {
    id: "mona-lisa-overdrive",
    title: "Mona Lisa Overdrive",
    author: "William Gibson",
    readDate: null,
    series: "sprawl",
    seriesOrder: 3,
    cover: "isbn:9781473217423",
    work: "OL27253W",
    accent: "#307db2",
  },
  {
    id: "the-peripheral",
    title: "The Peripheral",
    author: "William Gibson",
    readDate: "2024-12-09",
    series: "jackpot",
    seriesOrder: 1,
    cover: "olid:OL27164773M",
    accent: "#456b8b",
  },
  {
    id: "agency",
    title: "Agency",
    author: "William Gibson",
    readDate: null,
    series: "jackpot",
    seriesOrder: 2,
    cover: "id:13090570",
    work: "OL20639851W",
    accent: "#96533a",
  },
  {
    id: "permutation-city",
    title: "Permutation City",
    author: "Greg Egan",
    readDate: "2025-12-31",
    series: "egan-trilogy",
    seriesOrder: 1,
    cover: "isbn:9780575082076",
    work: "OL115336W",
    accent: "#386f81",
  },
  {
    id: "diaspora",
    title: "Diaspora",
    author: "Greg Egan",
    readDate: "2026-01-08",
    series: "egan-trilogy",
    seriesOrder: 2,
    cover: "id:1009216",
    work: "OL115341W",
    accent: "#5f5386",
  },
  {
    id: "prime-intellect",
    title: "The Metamorphosis of Prime Intellect",
    author: "Roger Williams",
    readDate: "2026-01-14",
    series: "prime-intellect",
    seriesOrder: 1,
    cover: "id:10201476",
    work: "OL20878335W",
    accent: "#7a353b",
  },
  {
    id: "schilds-ladder",
    title: "Schild’s Ladder",
    author: "Greg Egan",
    readDate: "2026-03-07",
    series: "egan-trilogy",
    seriesOrder: 3,
    cover: "id:379968",
    work: "OL115338W",
    accent: "#3d7d66",
  },
  {
    id: "daemon",
    title: "Daemon",
    author: "Daniel Suarez",
    readDate: "2026-03-25",
    series: "daemon",
    seriesOrder: 1,
    cover: "id:6404884",
    work: "OL13646905W",
    accent: "#734043",
  },
  {
    id: "freedom-tm",
    title: "Freedom™",
    author: "Daniel Suarez",
    readDate: "2026-03-29",
    series: "daemon",
    seriesOrder: 2,
    cover: "id:11420026",
    work: "OL21457048W",
    accent: "#8a7b3f",
  },
  {
    id: "fire-upon-deep",
    title: "A Fire Upon the Deep",
    author: "Vernor Vinge",
    readDate: "2026-07-21",
    series: "zones-thought",
    seriesOrder: 2,
    cover: "id:9261466",
    work: "OL1975714W",
    accent: "#8c4f35",
  },
  {
    id: "deepness-in-sky",
    title: "A Deepness in the Sky",
    author: "Vernor Vinge",
    readDate: null,
    series: "zones-thought",
    seriesOrder: 1,
    cover: "id:603591",
    work: "OL1975705W",
    accent: "#354d6a",
  },
  {
    id: "children-of-sky",
    title: "The Children of the Sky",
    author: "Vernor Vinge",
    readDate: null,
    series: "zones-thought",
    seriesOrder: 3,
    cover: "id:9907912",
    work: "OL16239463W",
    accent: "#4f755c",
  },
  {
    id: "accelerando",
    title: "Accelerando",
    author: "Charles Stross",
    readDate: "2026-08-26",
    series: "accelerando",
    seriesOrder: 1,
    status: "finishing",
    cover: "isbn:9780441014156",
    work: "OL2465670W",
    accent: "#3e6987",
  },
];

const SERIES = {
  remembrance: {
    name: "Thre Three-Body Trilogy",
    author: "Cixin Liu · with Baoshu’s coda",
    description: "Cosmic first contact on a scale that keeps widening.",
  },
  "children-time": {
    name: "Children of Time",
    author: "Adrian Tchaikovsky",
    description: "Evolution, machine minds and unlikely intelligence among the stars.",
  },
  teixcalaan: {
    name: "Teixcalaan",
    author: "Arkady Martine",
    description: "Imperial space opera with identity stored as inherited memory.",
  },
  bobiverse: {
    name: "Bobiverse",
    author: "Dennis E. Taylor",
    description: "One uploaded engineer, multiplied across a growing interstellar civilization.",
  },
  "ready-player": {
    name: "Ready Player",
    author: "Ernest Cline",
    description: "Life, power and nostalgia inside the OASIS.",
  },
  kovacs: {
    name: "Takeshi Kovacs",
    author: "Richard K. Morgan",
    description: "Bodies are sleeves; consciousness is the transferable asset.",
  },
  jackpot: {
    name: "Jackpot",
    author: "William Gibson",
    description: "Interleaved futures, telepresence and power across timelines.",
  },
  sprawl: {
    name: "Sprawl Trilogy",
    author: "William Gibson",
    description: "Cyberspace, artificial intelligence and high-tech lives at the edge of the matrix.",
  },
  "egan-trilogy": {
    name: "The Greg Egan Trilogy",
    author: "Greg Egan · Unofficial sequence",
    description: "Three standalone investigations of simulated selves, posthuman minds and reality at its limits.",
  },
  "prime-intellect": {
    name: "Prime Intellect",
    author: "Roger Williams · Standalone",
    description: "An omnipotent machine intelligence and the end of consequence.",
  },
  daemon: {
    name: "Daemon",
    author: "Daniel Suarez",
    description: "Autonomous software reorganizes a networked society.",
  },
  "zones-thought": {
    name: "Zones of Thought",
    author: "Vernor Vinge",
    description: "Intelligence itself changes across the geography of the galaxy.",
  },
  accelerando: {
    name: "Accelerando",
    author: "Charles Stross · Standalone",
    description: "Three generations cross the singularity and keep accelerating.",
  },
};

const DEFAULT_RATINGS = {
  "dark-forest": 10,
  "three-body-problem": 9.8,
  "ready-player-one": 9.6,
  "ready-player-two": 9.5,
  "permutation-city": 9.4,
  "deaths-end": 9.2,
  "prime-intellect": 9.2,
  "all-these-worlds": 9,
  daemon: 9,
  "freedom-tm": 9,
  "heavens-river": 9,
  "we-are-legion": 9,
  "for-we-are-many": 8.8,
  "not-till-lost": 8.8,
  "memory-called-empire": 8.6,
  "altered-carbon": 7.8,
  "redemption-of-time": 7.2,
  diaspora: 7,
  "the-peripheral": 7,
  "children-of-time": 6.4,
  "fire-upon-deep": 6,
  "schilds-ladder": 5.2,
  accelerando: 4.4,
};

const VIEW_META = {
  ranking: {
    title: "THE RANKING",
    description:
      "Artificial minds, uploaded selves, virtual worlds and intelligence among the stars—ordered by impact.",
  },
  series: {
    title: "SERIES INDEX",
    description:
      "Complete sequences at a glance. Pale, screened covers mark the volumes still waiting to be read.",
  },
  date: {
    title: "READ LOG",
    description:
      "A reverse-chronological flight recorder, from the current read back to the first contact.",
  },
};

const storageKey = "ai-fi-ratings-v2";
const legacyStorageKey = "ai-fi-ratings-v1";
const readDatesStorageKey = "ai-fi-read-dates-v1";
const editableHosts = new Set(["localhost", "127.0.0.1", "[::1]", "::1", "0.0.0.0"]);
const canEditRatings = editableHosts.has(window.location.hostname) || window.location.hostname.endsWith(".localhost");
const viewRoot = document.querySelector("#viewRoot");
const pageTitle = document.querySelector("#pageTitle");
const viewDescription = document.querySelector("#viewDescription");
const collectionStats = document.querySelector("#collectionStats");
const hero = document.querySelector(".hero");
const brandView = document.querySelector("#brandView");
const headerStats = document.querySelector("#headerStats");
const ratingDialog = document.querySelector("#ratingDialog");
const ratingForm = document.querySelector("#ratingForm");
const dialogBook = document.querySelector("#dialogBook");
const ratingInput = document.querySelector("#ratingInput");
const ratingOutput = document.querySelector("#ratingOutput");
const finishDateEditor = document.querySelector("#finishDateEditor");
const finishDateInput = document.querySelector("#finishDateInput");
const previousDayButton = document.querySelector("#previousDayButton");
const saveRatingButton = document.querySelector("#saveRating");
const removeRating = document.querySelector("#removeRating");
const aboutDialog = document.querySelector("#aboutDialog");
const exportRatingsButton = document.querySelector("#exportRatings");
const importRatingsButton = document.querySelector("#importRatings");
const importRatingsInput = document.querySelector("#importRatingsInput");
const transferStatus = document.querySelector("#transferStatus");
const ratingTransferCopy = document.querySelector("#ratingTransferCopy");
const canonicalReadDates = Object.fromEntries(
  BOOKS.filter((book) => book.readDate).map((book) => [book.id, book.readDate]),
);

let activeBookId = null;
let activeBookWasUnread = false;
let currentView = getInitialView();
let readDateOverrides = loadReadDates();
applyReadDates(readDateOverrides);
let ratings = loadRatings();

document.body.classList.toggle("is-readonly", !canEditRatings);
importRatingsButton.hidden = !canEditRatings;
ratingTransferCopy.textContent = canEditRatings
  ? "Move your ranking and locally recorded finish dates between browsers with a small JSON file."
  : "The published reading record is read-only. Download a JSON snapshot for safekeeping.";

function getInitialView() {
  const hashView = window.location.hash.replace("#", "");
  return VIEW_META[hashView] ? hashView : "ranking";
}

function normalizeDateValue(value) {
  if (typeof value !== "string" || !/^\d{4}-\d{2}-\d{2}$/.test(value)) return null;
  const date = new Date(`${value}T12:00:00`);
  return Number.isNaN(date.getTime()) ? null : value;
}

function localDateValue(date = new Date()) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function normalizeReadDates(candidate) {
  if (!candidate || typeof candidate !== "object") return {};

  return Object.fromEntries(
    Object.entries(candidate)
      .filter(([id, date]) => BOOKS.some((book) => book.id === id) && normalizeDateValue(date))
      .map(([id, date]) => [id, date]),
  );
}

function loadReadDates() {
  if (!canEditRatings) return {};

  try {
    return normalizeReadDates(JSON.parse(localStorage.getItem(readDatesStorageKey)));
  } catch {
    return {};
  }
}

function applyReadDates(overrides) {
  BOOKS.forEach((book) => {
    book.readDate = canonicalReadDates[book.id] || null;
  });

  Object.entries(overrides).forEach(([id, date]) => {
    const book = BOOKS.find((item) => item.id === id);
    if (book) book.readDate = date;
  });
}

function saveReadDates() {
  if (!canEditRatings) return;

  try {
    localStorage.setItem(readDatesStorageKey, JSON.stringify(readDateOverrides));
  } catch {
    // The shelf still works for the current session when storage is unavailable.
  }
}

function loadRatings() {
  if (!canEditRatings) return { ...DEFAULT_RATINGS };

  try {
    const stored = JSON.parse(localStorage.getItem(storageKey));
    if (stored && typeof stored === "object") return normalizeRatings(stored);

    const legacy = JSON.parse(localStorage.getItem(legacyStorageKey));
    const migrated = {
      ...DEFAULT_RATINGS,
      ...(legacy && typeof legacy === "object" ? normalizeRatings(legacy) : {}),
    };
    localStorage.setItem(storageKey, JSON.stringify(migrated));
    return migrated;
  } catch {
    return { ...DEFAULT_RATINGS };
  }
}

function normalizeRatings(candidate) {
  return Object.fromEntries(
    Object.entries(candidate)
      .filter(([id, rating]) => BOOKS.some((book) => book.id === id) && Number(rating) >= 1 && Number(rating) <= 10)
      .map(([id, rating]) => [id, Number(Number(rating).toFixed(1))]),
  );
}

function saveRatings() {
  if (!canEditRatings) return;

  try {
    localStorage.setItem(storageKey, JSON.stringify(ratings));
  } catch {
    // The shelf still works for the current session when storage is unavailable.
  }
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function coverUrl(book, size = "L") {
  const [type, value] = book.cover.split(":");
  return `https://covers.openlibrary.org/b/${type}/${value}-${size}.jpg?default=false`;
}

function displayDate(dateString, options = {}) {
  const date = new Date(`${dateString}T12:00:00`);
  return new Intl.DateTimeFormat("en-CA", {
    month: options.long ? "long" : "short",
    day: "numeric",
    year: "numeric",
  }).format(date);
}

function bookCover(book, extraClass = "") {
  return `
    <div class="book-cover-wrap ${extraClass}" style="--fallback-accent:${book.accent}">
      <div class="cover-fallback" aria-hidden="true">
        <span>AI—FI archive</span>
        <strong>${escapeHtml(book.title)}</strong>
        <span>${escapeHtml(book.author)}</span>
      </div>
      <img class="book-cover" data-cover src="${coverUrl(book)}" alt="Cover of ${escapeHtml(book.title)}" loading="lazy" />
      ${book.status === "finishing" ? '<span class="current-ribbon">Finishing 08.26</span>' : ""}
    </div>`;
}

function bookCard(book, { rank = null, index = 0, todo = false, context = "default", yearMarker = null } = {}) {
  const rating = ratings[book.id];
  const meta = todo
    ? `Book ${book.orderLabel || book.seriesOrder} · To read`
    : book.status === "finishing"
      ? "Finishing tomorrow"
      : `Read ${displayDate(book.readDate)}`;

  const inner = `
    ${bookCover(book)}
    ${rank ? `<span class="rank-marker">${String(rank).padStart(2, "0")}</span>` : ""}
    ${yearMarker ? `<span class="year-marker">${yearMarker}</span>` : ""}
    ${todo ? '<span class="todo-stamp">To read</span>' : ""}
    <div class="book-meta">
      <div>
        ${context === "series" ? "" : `<h3 class="book-title" title="${escapeHtml(book.title)}">${escapeHtml(book.title)}</h3>`}
        ${context === "series" ? "" : `<p class="book-author">${escapeHtml(book.author)}</p>`}
        ${context === "series" ? "" : `<p class="book-date">${meta}</p>`}
      </div>
      ${rating ? `<span class="rating-chip">${Number(rating).toFixed(1)}<small>/10</small></span>` : ""}
    </div>`;

  if (todo) {
    if (!canEditRatings) {
      return `<article class="book-card is-todo is-readonly" style="--index:${index}">${inner}</article>`;
    }

    return `
      <article class="book-card is-todo" style="--index:${index}">
        <button class="book-trigger" type="button" data-rate-book="${book.id}" aria-label="Mark ${escapeHtml(book.title)} finished and rate it">
          ${inner}
        </button>
      </article>`;
  }

  if (!canEditRatings) {
    return `<article class="book-card is-readonly" style="--index:${index}">${inner}</article>`;
  }

  return `
    <article class="book-card ${context === "current" ? "is-current" : ""}" style="--index:${index}">
      <button class="book-trigger" type="button" data-rate-book="${book.id}" aria-label="Rate ${escapeHtml(book.title)}">
        ${inner}
      </button>
    </article>`;
}

function queueItem(book) {
  const status = book.status === "finishing" ? "Finishing Aug 26 · Rate when done" : `Read ${displayDate(book.readDate)}`;
  return `
    <button class="queue-item ${book.status === "finishing" ? "is-current" : ""}" type="button" data-rate-book="${book.id}">
      <span class="queue-cover" style="--fallback-accent:${book.accent}">
        <span class="cover-fallback" aria-hidden="true"><span></span><strong>${escapeHtml(book.title)}</strong><span></span></span>
        <img data-cover src="${coverUrl(book, "M")}" alt="" loading="lazy" />
      </span>
      <span class="queue-copy">
        <strong>${escapeHtml(book.title)}</strong>
        <span>${status}</span>
      </span>
      <span class="rate-arrow" aria-hidden="true">+</span>
    </button>`;
}

function seriesAverage(seriesId) {
  const scored = BOOKS.filter(
    (book) => book.series === seriesId && book.countsTowardAverage !== false && ratings[book.id],
  ).map((book) => ratings[book.id]);
  if (!scored.length) return null;
  return scored.reduce((sum, value) => sum + Number(value), 0) / scored.length;
}

function renderStats() {
  const readCount = BOOKS.filter((book) => book.readDate && book.status !== "finishing").length;
  const ratedCount = Object.keys(ratings).length;
  const todoCount = BOOKS.filter((book) => !book.readDate).length;
  const stats =
    currentView === "series"
      ? [
          [Object.keys(SERIES).length, "Series / signals"],
          [todoCount, "To read"],
          [readCount, "Read"],
        ]
      : currentView === "date"
        ? [
            [readCount, "Finished"],
            ["2.8 yr", "Reading span"],
            ["1 now", "In progress"],
          ]
        : [
            [ratedCount, "Ranked"],
            [readCount, "Read"],
            [readCount - ratedCount + 1, "Awaiting score"],
          ];

  collectionStats.innerHTML = stats
    .map(([value, label]) => `<div class="stat"><strong>${value}</strong><span>${label}</span></div>`)
    .join("");
}

function renderRanking() {
  const ranked = BOOKS.filter((book) => ratings[book.id]).sort((a, b) => {
    const byRating = ratings[b.id] - ratings[a.id];
    return byRating || a.title.localeCompare(b.title);
  });
  const queue = BOOKS.filter((book) => book.readDate && !ratings[book.id]).sort((a, b) => {
    if (a.status === "finishing") return -1;
    if (b.status === "finishing") return 1;
    return new Date(b.readDate) - new Date(a.readDate);
  });

  viewRoot.innerHTML = `
    <div class="view-heading-row">
      <h2 class="section-label">Rated transmission</h2>
      <span class="sort-note">Highest signal first</span>
    </div>
    <div class="ranking-layout ${canEditRatings && queue.length ? "" : "is-complete"}">
      <div class="ranked-grid">
        ${
          ranked.length
            ? ranked.map((book, index) => bookCard(book, { rank: index + 1, index })).join("")
            : `<div class="empty-ranking"><h3>The ranking is open.</h3><p>Score a finished book from the queue and it will land here automatically.</p></div>`
        }
      </div>
      ${
        canEditRatings && queue.length
          ? `<aside class="queue-panel">
              <div class="queue-heading"><h2>Waiting for a score</h2><span>${queue.length}</span></div>
              <p class="queue-intro">Read, remembered, not yet ranked. Choose a title to give it a score out of ten.</p>
              <div class="queue-list">${queue.map(queueItem).join("")}</div>
            </aside>`
          : ""
      }
    </div>`;
}

function renderSeries() {
  const groups = Object.entries(SERIES)
    .map(([id, meta]) => ({
      id,
      ...meta,
      average: seriesAverage(id),
      books: BOOKS.filter((book) => book.series === id).sort((a, b) => a.seriesOrder - b.seriesOrder),
    }))
    .sort((a, b) => {
      if (a.average === null && b.average === null) return a.name.localeCompare(b.name);
      if (a.average === null) return 1;
      if (b.average === null) return -1;
      return b.average - a.average || a.name.localeCompare(b.name);
    });

  viewRoot.innerHTML = `
    <div class="view-heading-row">
      <h2 class="section-label">Series architecture</h2>
      <span class="sort-note">Sorted by rated average · unrated after</span>
    </div>
    <div class="series-list">
      ${groups
        .map(
          (group, groupIndex) => `
          <section class="series-block" style="--index:${groupIndex}">
            <div class="series-copy">
              <span class="series-number">${String(groupIndex + 1).padStart(2, "0")} / ${String(groups.length).padStart(2, "0")}</span>
              <h2>${escapeHtml(group.name)}</h2>
              <p>${escapeHtml(group.author)}</p>
              <p>${escapeHtml(group.description)}</p>
              <div class="series-score">
                ${group.average === null ? "—" : group.average.toFixed(1)}
                <small>${group.average === null ? "Unrated" : "Avg / 10"}</small>
              </div>
            </div>
            <div class="series-books ${group.books.length > 3 ? "is-long" : ""}" style="--book-count:${group.books.length}">
              ${group.books.map((book, index) => bookCard(book, { index, todo: !book.readDate, context: "series" })).join("")}
            </div>
          </section>`,
        )
        .join("")}
    </div>`;
}

function renderDate() {
  const dated = BOOKS.filter((book) => book.readDate).sort((a, b) => new Date(b.readDate) - new Date(a.readDate));

  viewRoot.innerHTML = `
    <div class="view-heading-row">
      <h2 class="section-label">Reading flight recorder</h2>
      <span class="sort-note">Newest first · Continuous across years</span>
    </div>
    <section class="date-flow">
      <div class="date-grid">
        ${dated
          .map((book, index) => {
            const year = book.readDate.slice(0, 4);
            const previousYear = index ? dated[index - 1].readDate.slice(0, 4) : null;
            return bookCard(book, {
              index,
              context: book.status === "finishing" ? "current" : "default",
              yearMarker: year !== previousYear ? year : null,
            });
          })
          .join("")}
      </div>
    </section>`;
}

function hydrateCoverImages(root = document) {
  root.querySelectorAll("img[data-cover]").forEach((image) => {
    const wrapper = image.closest(".book-cover-wrap, .queue-cover, .dialog-book");
    const show = () => wrapper?.classList.add("has-image");
    const fail = () => {
      wrapper?.classList.remove("has-image");
      image.remove();
    };
    if (image.complete) {
      image.naturalWidth > 1 ? show() : fail();
    } else {
      image.addEventListener("load", show, { once: true });
      image.addEventListener("error", fail, { once: true });
    }
  });
}

function render() {
  const readCount = BOOKS.filter((book) => book.readDate && book.status !== "finishing").length;
  const ratedCount = Object.keys(ratings).length;
  const todoCount = BOOKS.filter((book) => !book.readDate).length;

  hero.classList.add("is-collapsed");
  viewRoot.classList.add("is-compact-view");
  brandView.hidden = false;
  headerStats.hidden = false;
  brandView.textContent = VIEW_META[currentView].title;
  headerStats.innerHTML =
    currentView === "series"
      ? `<strong>${Object.keys(SERIES).length}</strong> series <i>·</i> <strong>${todoCount}</strong> to read <i>·</i> <strong>${readCount}</strong> read`
      : currentView === "date"
        ? `<strong>${readCount}</strong> finished <i>·</i> <strong>2.8</strong> yr span <i>·</i> <strong>1</strong> now`
        : `<strong>${ratedCount}</strong> ranked <i>·</i> <strong>${readCount}</strong> read`;

  document.querySelectorAll(".view-button").forEach((button) => {
    const isActive = button.dataset.view === currentView;
    button.classList.toggle("is-active", isActive);
    button.setAttribute("aria-current", isActive ? "page" : "false");
  });

  pageTitle.innerHTML = VIEW_META[currentView].title;
  viewDescription.textContent = VIEW_META[currentView].description;
  renderStats();

  if (currentView === "series") renderSeries();
  else if (currentView === "date") renderDate();
  else renderRanking();

  hydrateCoverImages(viewRoot);
}

function openRating(bookId) {
  if (!canEditRatings) return;

  const book = BOOKS.find((item) => item.id === bookId);
  if (!book) return;
  activeBookId = book.id;
  activeBookWasUnread = !book.readDate;
  const currentRating = ratings[book.id];
  ratingInput.value = currentRating || 8;
  ratingOutput.value = Number(ratingInput.value).toFixed(1);
  removeRating.hidden = activeBookWasUnread || !currentRating;
  finishDateEditor.hidden = !activeBookWasUnread;
  finishDateInput.disabled = !activeBookWasUnread;
  finishDateInput.required = activeBookWasUnread;
  finishDateInput.value = activeBookWasUnread ? localDateValue() : book.readDate;
  finishDateInput.setCustomValidity("");
  saveRatingButton.textContent = activeBookWasUnread ? "Finish + add to ranking" : "Save to ranking";

  const series = SERIES[book.series];
  const readingStatus = activeBookWasUnread
    ? `Ready to finish · ${series ? series.name : "Unread"}`
    : book.status === "finishing"
      ? "Finishing Aug 26, 2026"
      : `Read ${displayDate(book.readDate, { long: true })}`;

  dialogBook.innerHTML = `
    <div class="cover-fallback" style="--fallback-accent:${book.accent}" aria-hidden="true">
      <span>AI—FI archive</span><strong>${escapeHtml(book.title)}</strong><span>${escapeHtml(book.author)}</span>
    </div>
    <img data-cover src="${coverUrl(book)}" alt="Cover of ${escapeHtml(book.title)}" />
    <div class="dialog-book-copy">
      <h2>${escapeHtml(book.title)}</h2>
      <p>${escapeHtml(book.author)} · ${escapeHtml(readingStatus)}</p>
    </div>`;

  hydrateCoverImages(dialogBook);
  ratingDialog.showModal();
}

document.querySelectorAll(".view-button").forEach((button) => {
  button.addEventListener("click", () => {
    currentView = button.dataset.view;
    history.replaceState(null, "", `#${currentView}`);
    render();
    window.scrollTo({ top: document.querySelector(".hero").offsetTop, behavior: "smooth" });
  });
});

viewRoot.addEventListener("click", (event) => {
  const trigger = event.target.closest("[data-rate-book]");
  if (trigger) openRating(trigger.dataset.rateBook);
});

ratingInput.addEventListener("input", () => {
  ratingOutput.value = Number(ratingInput.value).toFixed(1);
});

finishDateInput.addEventListener("input", () => finishDateInput.setCustomValidity(""));

previousDayButton.addEventListener("click", () => {
  const selectedDate = normalizeDateValue(finishDateInput.value) || localDateValue();
  const previousDate = new Date(`${selectedDate}T12:00:00`);
  previousDate.setDate(previousDate.getDate() - 1);
  finishDateInput.value = localDateValue(previousDate);
  finishDateInput.setCustomValidity("");
});

ratingForm.addEventListener("submit", (event) => {
  if (!canEditRatings) return;

  const action = event.submitter?.value;
  if (!activeBookId || !["save", "remove"].includes(action)) return;

  event.preventDefault();
  if (action === "remove") delete ratings[activeBookId];
  else {
    if (activeBookWasUnread) {
      const finishDate = normalizeDateValue(finishDateInput.value);
      if (!finishDate) {
        finishDateInput.setCustomValidity("Choose a valid finish date.");
        finishDateInput.reportValidity();
        return;
      }

      const book = BOOKS.find((item) => item.id === activeBookId);
      readDateOverrides[activeBookId] = finishDate;
      if (book) book.readDate = finishDate;
      saveReadDates();
    }

    ratings[activeBookId] = Number(Number(ratingInput.value).toFixed(1));
  }

  saveRatings();
  ratingDialog.close(action);
  render();
});

document.querySelector("#aboutButton").addEventListener("click", () => aboutDialog.showModal());

exportRatingsButton.addEventListener("click", () => {
  const payload = {
    app: "AI-FI",
    version: 2,
    exportedAt: new Date().toISOString(),
    ratings,
    readDates: Object.fromEntries(
      BOOKS.filter((book) => book.readDate).map((book) => [book.id, book.readDate]),
    ),
  };
  const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `ai-fi-ratings-${new Date().toISOString().slice(0, 10)}.json`;
  document.body.append(link);
  link.click();
  link.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 0);
  transferStatus.textContent = `${Object.keys(ratings).length} ratings exported.`;
});

importRatingsButton.addEventListener("click", () => {
  if (canEditRatings) importRatingsInput.click();
});

importRatingsInput.addEventListener("change", async () => {
  if (!canEditRatings) return;

  const [file] = importRatingsInput.files;
  if (!file) return;

  try {
    const payload = JSON.parse(await file.text());
    const imported = normalizeRatings(payload.ratings || payload);
    const hasReadDates = payload.readDates && typeof payload.readDates === "object";
    const importedReadDates = normalizeReadDates(payload.readDates);
    if (!Object.keys(imported).length && !Object.keys(importedReadDates).length) {
      throw new Error("No valid reading data found");
    }

    ratings = imported;
    if (hasReadDates) {
      readDateOverrides = importedReadDates;
      applyReadDates(readDateOverrides);
      saveReadDates();
    }
    saveRatings();
    render();
    transferStatus.textContent = `${Object.keys(imported).length} ratings and ${Object.keys(importedReadDates).length} finish dates imported.`;
  } catch {
    transferStatus.textContent = "That file does not contain a valid AI-FI ratings backup.";
  } finally {
    importRatingsInput.value = "";
  }
});

[ratingDialog, aboutDialog].forEach((dialog) => {
  dialog.addEventListener("click", (event) => {
    if (event.target === dialog) dialog.close("cancel");
  });
});

window.addEventListener("hashchange", () => {
  const hashView = window.location.hash.replace("#", "");
  if (VIEW_META[hashView] && hashView !== currentView) {
    currentView = hashView;
    render();
  }
});

render();
