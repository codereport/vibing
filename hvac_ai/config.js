// Public browser configuration only. Never put a Gemini API key in this file.
(() => {
    const isLocal = ['localhost', '127.0.0.1'].includes(window.location.hostname);
    window.HVAC_APP_CONFIG = Object.freeze({
        aiAnalyzeEndpoint: isLocal
            ? 'http://localhost:8787/analyze'
            : 'https://hvac-equipment-analyzer.hvac-equipment-analyzer.workers.dev/analyze',
        aiAnalyzeTimeoutMs: 45000
    });
})();
