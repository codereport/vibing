document.addEventListener('DOMContentLoaded', () => {
    const themeSwitch = document.getElementById('theme-switch');
    const icon = themeSwitch.querySelector('i');
    const body = document.body;

    // Check for saved theme preference, otherwise use system preference
    const savedTheme = localStorage.getItem('theme');
    const systemPrefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;

    if (savedTheme === 'dark' || (!savedTheme && systemPrefersDark)) {
        enableDarkMode();
    }

    themeSwitch.addEventListener('click', () => {
        if (body.getAttribute('data-theme') === 'dark') {
            disableDarkMode();
        } else {
            enableDarkMode();
        }
    });

    function enableDarkMode() {
        body.setAttribute('data-theme', 'dark');
        icon.classList.remove('fa-moon');
        icon.classList.add('fa-sun');
        localStorage.setItem('theme', 'dark');
    }

    function disableDarkMode() {
        body.removeAttribute('data-theme');
        icon.classList.remove('fa-sun');
        icon.classList.add('fa-moon');
        localStorage.setItem('theme', 'light');
    }

    // Set current year in footer
    document.getElementById('year').textContent = new Date().getFullYear();

    // Stats Toggle
    document.addEventListener('keydown', (e) => {
        if (e.key === 's' || e.key === 'S') {
            document.body.classList.toggle('show-stats');
        }
    });
});
