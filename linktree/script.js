document.addEventListener('DOMContentLoaded', () => {
    // Set current year in footer
    document.getElementById('year').textContent = new Date().getFullYear();

    // Stats Toggle
    function toggleStats() {
        document.body.classList.toggle('show-stats');
    }

    document.addEventListener('keydown', (e) => {
        if (e.key === 's' || e.key === 'S') {
            toggleStats();
        }
    });

    window.addEventListener('message', (event) => {
        if (event.data === 'toggle-stats') {
            toggleStats();
        }
    });
});
