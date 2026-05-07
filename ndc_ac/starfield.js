const LOGO_BASE = 'https://raw.githubusercontent.com/codereport/logos/main/';
const LOGO_FILES = [
  'python.png', 'haskell.svg', 'cpp.png', 'rust_darkmode.png',
  'java.png', 'javascript.png', 'go.png', 'scala.svg',
  'kotlin.svg', 'ruby.png', 'elixir.png', 'clojure.png',
  'swift.png', 'julia.png', 'apl.png', 'bqn.svg',
  'fsharp.png', 'csharp.png', 'd.png', 'r.png',
];

const logos = [];
LOGO_FILES.forEach(f => {
  const img = new Image();
  img.src = LOGO_BASE + f;
  logos.push(img);
});

const canvas = document.getElementById('warp');
const ctx = canvas.getContext('2d');

function resize() {
  canvas.width = window.innerWidth * devicePixelRatio;
  canvas.height = window.innerHeight * devicePixelRatio;
  ctx.setTransform(devicePixelRatio, 0, 0, devicePixelRatio, 0, 0);
}
window.addEventListener('resize', resize);
resize();

const W = () => window.innerWidth;
const H = () => window.innerHeight;

const STAR_COUNT = 50;
const MAX_Z = 15;
const MIN_Z = 0.2;
const SPEED = 5;
const BASE_SIZE = 70;
const SPREAD = 600;
const stars = [];

function makeStar(stagger) {
  return {
    x: (Math.random() - 0.5) * SPREAD,
    y: (Math.random() - 0.5) * SPREAD,
    z: stagger ? MIN_Z + Math.random() * (MAX_Z - MIN_Z) : MAX_Z - Math.random() * 2,
    logo: logos[Math.floor(Math.random() * logos.length)],
  };
}

for (let i = 0; i < STAR_COUNT; i++) stars.push(makeStar(true));

let animId;
let lastTime = performance.now();

function animate(now) {
  const dt = (now - lastTime) / 1000;
  lastTime = now;
  const cx = W() / 2;
  const cy = H() / 2;

  ctx.clearRect(0, 0, W(), H());

  for (let i = 0; i < stars.length; i++) {
    const s = stars[i];
    s.z -= SPEED * dt;

    if (s.z <= MIN_Z) {
      stars[i] = makeStar(false);
      continue;
    }

    if (!s.logo.complete || !s.logo.naturalWidth) continue;

    const scale = 1 / s.z;
    const sx = cx + s.x * scale;
    const sy = cy + s.y * scale;
    const size = BASE_SIZE * scale;

    if (sx + size < 0 || sx - size > W() || sy + size < 0 || sy - size > H()) {
      stars[i] = makeStar(false);
      continue;
    }

    const t = 1 - (s.z - MIN_Z) / (MAX_Z - MIN_Z);
    const opacity = 0.1 + t * 0.55;

    ctx.save();
    ctx.globalAlpha = opacity;
    ctx.drawImage(s.logo, sx - size / 2, sy - size / 2, size, size);
    ctx.restore();
  }

  animId = requestAnimationFrame(animate);
}
animId = requestAnimationFrame(animate);

const iframe = document.querySelector('iframe');
iframe.addEventListener('load', () => {
  setTimeout(() => {
    iframe.classList.add('ready');
    setTimeout(() => {
      cancelAnimationFrame(animId);
    }, 400);
  }, 1000);
});

function lock() {
  iframe.classList.add('locked');
  iframe.classList.remove('interactive');
  window.focus();
}

function unlock() {
  iframe.classList.remove('locked');
  iframe.classList.add('interactive');
}

document.addEventListener('keydown', (e) => {
  if (e.key === 'e' || e.key === 'E') unlock();
});

document.addEventListener('click', (e) => {
  if (e.target !== iframe) lock();
});
