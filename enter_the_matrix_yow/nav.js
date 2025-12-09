// Navigation Logic
const pages = [
    'index.html',
    'qr.html',
    'linktree.html',
    'qr_pres.html',
    'linktree.html',
    'index.html',
    'topics.html',
    'ai.html',
    'red_blue_pill.html',
    'adsp_high_on_ai.html',
    'ai_coding.html',
    'ai_tips.html',
    'ai_analysis.html',
    'ai_tips.html',
    // 'matrix_fight.html',
    'matrix_clip_fight.html',
    'matrix_clip_air.html',
    'matrix_clip_know.html',
    // 'ai_tips.html',
    'blink.html',
    'metric_6_1.html',
    'metric_6_2.html',
    'metric_6_3.html',
    'blink.html',
    'rust_js.html',
    'topics.html',
    'array.html',
    'array_programming.html',
    'bqn_pad.html',
    'tryapl.html',
    'uiua_pad.html',
    'j_playground.html',
    'array_comparison_nb.html',
    'array_comparison.html',
    'blink.html',
    'mapadj.html',
    'swap.html',
    'topics.html',
    'gpu.html',
    'blink_bqn_parrot.html',
    'cuda_libraries.html',
    'parrot_sushi.html',
    'summary.html',
    'matrix_clip_know.html',
    'by_the_way.html',
    'made_with_ai.html',
    'thank_you.html',
    // 'quad_pad.html',
];

function navigate(offset) {
    const pathname = window.location.pathname;
    const currentPage = pathname.split('/').pop() || 'index.html';

    // Find all indices that match the current page
    const candidateIndices = pages.map((p, index) => p.endsWith(currentPage) ? index : -1).filter(i => i !== -1);

    if (candidateIndices.length === 0) return;

    // Use sessionStorage to store state, or closest match logic
    let currentIndex = candidateIndices[0];
    const storedIndex = parseInt(sessionStorage.getItem('vibing_nav_index'));

    if (!isNaN(storedIndex)) {
        // Find the candidate index closest to the stored index
        // This handles back button usage and loops gracefully
        currentIndex = candidateIndices.reduce((prev, curr) => {
            return (Math.abs(curr - storedIndex) < Math.abs(prev - storedIndex) ? curr : prev);
        });
    } else if (candidateIndices.length > 1) {
        // Fallback if no session state (e.g. first load):
        currentIndex = candidateIndices[0];
    }

    const nextIndex = currentIndex + offset;

    // Check bounds
    if (nextIndex >= 0 && nextIndex < pages.length) {
        sessionStorage.setItem('vibing_nav_index', nextIndex);
        window.location.href = pages[nextIndex];
    }
}

document.addEventListener('keydown', (e) => {
    if (e.key === 'f' || e.key === 'F') {
        // Toggle fullscreen on 'f' key
        if (!document.fullscreenElement) {
            document.documentElement.requestFullscreen();
        } else {
            document.exitFullscreen();
        }
        return;
    }

    if (e.key === 'ArrowLeft' || e.key === 'PageUp') {
        navigate(-1);
    } else if (e.key === 'ArrowRight' || e.key === 'PageDown') {
        navigate(1);
    }
});

// Touch handling for swipe navigation
let touchStartX = 0;
let touchStartY = 0;

document.addEventListener('touchstart', (e) => {
    touchStartX = e.changedTouches[0].screenX;
    touchStartY = e.changedTouches[0].screenY;
}, { passive: true });

document.addEventListener('touchend', (e) => {
    const touchEndX = e.changedTouches[0].screenX;
    const touchEndY = e.changedTouches[0].screenY;
    handleSwipe(touchStartX, touchStartY, touchEndX, touchEndY);
}, { passive: true });

function handleSwipe(startX, startY, endX, endY) {
    const diffX = endX - startX;
    const diffY = endY - startY;

    // Threshold for swipe detection (e.g., 50px)
    // Also ensure horizontal swipe is more significant than vertical movement
    if (Math.abs(diffX) > Math.abs(diffY) && Math.abs(diffX) > 50) {
        if (diffX > 0) {
            // Swipe Right -> Previous
            navigate(-1);
        } else {
            // Swipe Left -> Next
            navigate(1);
        }
    }
}

// Create and inject mobile navigation buttons
function createMobileNavButtons() {
    // Inject CSS
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
            pointer-events: none; /* Let clicks pass through the container */
        }
        .nav-btn {
            background: rgba(0, 0, 0, 0.5);
            color: #00ff00;
            border: 2px solid #00ff00;
            border-radius: 50%;
            width: 60px;
            height: 60px;
            font-size: 24px;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            pointer-events: auto; /* Re-enable clicks for buttons */
            backdrop-filter: blur(5px);
            box-shadow: 0 0 10px #00ff00;
            transition: transform 0.2s, background 0.2s;
        }
        .nav-btn:active {
            transform: scale(0.95);
            background: rgba(0, 255, 0, 0.2);
        }
        @media (max-width: 768px) {
            .mobile-nav {
                display: flex;
            }
        }
    `;
    document.head.appendChild(style);

    // Create Elements
    const container = document.createElement('div');
    container.className = 'mobile-nav';

    const prevBtn = document.createElement('button');
    prevBtn.className = 'nav-btn prev';
    prevBtn.innerHTML = '❮';
    prevBtn.onclick = () => navigate(-1);

    const nextBtn = document.createElement('button');
    nextBtn.className = 'nav-btn next';
    nextBtn.innerHTML = '❯';
    nextBtn.onclick = () => navigate(1);

    container.appendChild(prevBtn);
    container.appendChild(nextBtn);
    document.body.appendChild(container);
}

// Initialize mobile nav buttons
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', createMobileNavButtons);
} else {
    createMobileNavButtons();
}
