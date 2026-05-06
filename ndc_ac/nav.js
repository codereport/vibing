const pages = [
    'index.html',
    'linktree.html',
    'bio.html',
    'trilogies.html',
    'drstrange.html',
    'poll.html',
];

function navigate(offset) {
    const pathname = window.location.pathname;
    const currentPage = pathname.split('/').pop() || 'index.html';

    const candidateIndices = pages.map((p, index) => p.endsWith(currentPage) ? index : -1).filter(i => i !== -1);
    if (candidateIndices.length === 0) return;

    let currentIndex = candidateIndices[0];
    const storedIndex = parseInt(sessionStorage.getItem('vibing_nav_index'));

    if (!isNaN(storedIndex)) {
        currentIndex = candidateIndices.reduce((prev, curr) =>
            Math.abs(curr - storedIndex) < Math.abs(prev - storedIndex) ? curr : prev
        );
    }

    const nextIndex = currentIndex + offset;
    if (nextIndex >= 0 && nextIndex < pages.length) {
        sessionStorage.setItem('vibing_nav_index', nextIndex);
        window.location.href = pages[nextIndex];
    }
}

document.addEventListener('keydown', (e) => {
    if (e.key === 'f' || e.key === 'F') {
        if (!document.fullscreenElement) {
            document.documentElement.requestFullscreen();
        } else {
            document.exitFullscreen();
        }
        return;
    }
    if (e.key === 'ArrowLeft' || e.key === 'PageUp') navigate(-1);
    if (e.key === 'ArrowRight' || e.key === 'PageDown') navigate(1);
});

let touchStartX = 0;
let touchStartY = 0;

document.addEventListener('touchstart', (e) => {
    touchStartX = e.changedTouches[0].screenX;
    touchStartY = e.changedTouches[0].screenY;
}, { passive: true });

document.addEventListener('touchend', (e) => {
    const touchEndX = e.changedTouches[0].screenX;
    const touchEndY = e.changedTouches[0].screenY;
    const diffX = touchEndX - touchStartX;
    const diffY = touchEndY - touchStartY;
    if (Math.abs(diffX) > Math.abs(diffY) && Math.abs(diffX) > 50) {
        navigate(diffX > 0 ? -1 : 1);
    }
}, { passive: true });

function createMobileNavButtons() {
    const style = document.createElement('style');
    style.textContent = `
        .mobile-nav {
            display: none;
            position: fixed;
            bottom: 20px;
            left: 0;
            width: 100%;
            justify-content: space-between;
            padding: 0 20px;
            z-index: 1000;
            pointer-events: none;
        }
        .nav-btn {
            background: rgba(0, 0, 0, 0.5);
            color: #fff;
            border: 2px solid rgba(255,255,255,0.3);
            border-radius: 50%;
            width: 60px;
            height: 60px;
            font-size: 24px;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            pointer-events: auto;
            backdrop-filter: blur(5px);
            transition: transform 0.2s, background 0.2s;
        }
        .nav-btn:active {
            transform: scale(0.95);
            background: rgba(255, 255, 255, 0.15);
        }
        @media (max-width: 768px) {
            .mobile-nav { display: flex; }
        }
    `;
    document.head.appendChild(style);

    const container = document.createElement('div');
    container.className = 'mobile-nav';

    const prevBtn = document.createElement('button');
    prevBtn.className = 'nav-btn prev';
    prevBtn.innerHTML = '&#10094;';
    prevBtn.onclick = () => navigate(-1);

    const nextBtn = document.createElement('button');
    nextBtn.className = 'nav-btn next';
    nextBtn.innerHTML = '&#10095;';
    nextBtn.onclick = () => navigate(1);

    container.appendChild(prevBtn);
    container.appendChild(nextBtn);
    document.body.appendChild(container);
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', createMobileNavButtons);
} else {
    createMobileNavButtons();
}
