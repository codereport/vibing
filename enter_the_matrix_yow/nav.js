// Navigation Logic
const pages = [
    'index.html',
    'qr.html',
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
    'matrix_fight.html',
    'ai_tips.html',
    'rust_js.html',
    'blink.html',
    'metric_6_1.html',
    'metric_6_2.html',
    'metric_6_3.html',
    'blink.html',
    'topics.html',
    'array.html',
    'array_programming.html',
    'bqn_pad.html',
    'tryapl.html',
    'uiua_pad.html',
    'j_playground.html',
    'array_comparison.html',
    'topics.html',
    'gpu.html',
    'blink_bqn_parrot.html',
    'cuda_libraries.html',
    'parrot_sushi.html',
    'summary.html',
    'by_the_way.html',
    'made_with_ai.html',
    'thank_you.html',
    // 'quad_pad.html',
];

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

    if (e.key === 'ArrowLeft' || e.key === 'ArrowRight') {
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
            // If multiple candidates, we might use referrer as a tie breaker,
            // but usually default to 0 is fine for start.
            // However, if we are really at index 3 (e.g. manually typed URL), 0 might be wrong.
            // But without state, 0 is the safest start.
            currentIndex = candidateIndices[0];
        }

        let nextIndex;
        if (e.key === 'ArrowLeft') {
            nextIndex = currentIndex - 1;
        } else {
            nextIndex = currentIndex + 1;
        }

        // Check bounds
        if (nextIndex >= 0 && nextIndex < pages.length) {
            sessionStorage.setItem('vibing_nav_index', nextIndex);
            window.location.href = pages[nextIndex];
        }
    }
});
