import test from 'node:test';
import assert from 'node:assert/strict';
import worker, { sanitizeGeminiResult, validateImages } from '../src/index.js';

const tinyJpeg = 'data:image/jpeg;base64,/9j/4AAQSkZJRg==';

test('accepts labelled rating-plate image data URLs', () => {
    const images = validateImages({ images: [{ kind: 'furnace', dataUrl: tinyJpeg }] });
    assert.equal(images.length, 1);
    assert.equal(images[0].mimeType, 'image/jpeg');
});

test('rejects unsupported image types and too many photos', () => {
    assert.throws(() => validateImages({ images: [{ kind: 'furnace', dataUrl: 'data:image/gif;base64,AAAA' }] }), /JPEG, PNG, or WebP/);
    assert.throws(() => validateImages({ images: Array.from({ length: 5 }, () => ({ kind: 'cooling', dataUrl: tinyJpeg })) }), /between 1 and 4/);
});

test('sanitizes model data and rejects implausible values', () => {
    const result = sanitizeGeminiResult({
        furnace: { model: ' el296uh070xv36b ', serial: '1234a56789', inputBtu: 70000, outputBtu: 250000, afue: 96, type: 'high_eff_gas', confidence: 91, plateText: 'MODEL', notes: '' },
        cooling: { model: 'ml14xc1-036', serial: 'bad serial!', tons: 3, efficiency: 14, type: 'ac', confidence: 88 },
        warnings: ['Verify against plate']
    });
    assert.equal(result.furnace.model, 'EL296UH070XV36B');
    assert.equal(result.furnace.outputBtu, null);
    assert.equal(result.cooling.model, 'ML14XC1-036');
    assert.equal(result.warnings[0], 'Verify against plate');
});

test('Worker proxies a valid request and returns CORS-safe structured data', async () => {
    const originalFetch = globalThis.fetch;
    globalThis.fetch = async (url, options) => {
        assert.match(String(url), /gemini-2\.5-flash-lite:generateContent$/);
        assert.equal(options.headers['x-goog-api-key'], 'test-secret');
        const request = JSON.parse(options.body);
        assert.equal(request.contents[0].parts[2].inline_data.mime_type, 'image/jpeg');
        return new Response(JSON.stringify({
            candidates: [{ content: { parts: [{ text: JSON.stringify({
                furnace: { model: 'EL296UH070XV36B', serial: '1234A56789', inputBtu: 70000, outputBtu: 67000, afue: 96, type: 'high_eff_gas', confidence: 94, plateText: 'MODEL EL296UH070XV36B', notes: null },
                cooling: null,
                warnings: []
            }) }] } }],
            usageMetadata: { promptTokenCount: 100 }
        }), { status: 200, headers: { 'Content-Type': 'application/json' } });
    };

    try {
        const request = new Request('https://worker.example/analyze', {
            method: 'POST',
            headers: { Origin: 'https://example.github.io', 'Content-Type': 'application/json' },
            body: JSON.stringify({ images: [{ kind: 'furnace', dataUrl: tinyJpeg }] })
        });
        const response = await worker.fetch(request, { GEMINI_API_KEY: 'test-secret', ALLOWED_ORIGINS: 'https://example.github.io' });
        const body = await response.json();
        assert.equal(response.status, 200);
        assert.equal(response.headers.get('Access-Control-Allow-Origin'), 'https://example.github.io');
        assert.equal(body.furnace.inputBtu, 70000);
        assert.equal(body.model, 'gemini-2.5-flash-lite');
        assert.equal(JSON.stringify(body).includes('test-secret'), false);
    } finally {
        globalThis.fetch = originalFetch;
    }
});

test('Worker rejects browser origins outside the allowlist', async () => {
    const request = new Request('https://worker.example/analyze', {
        method: 'POST',
        headers: { Origin: 'https://attacker.example', 'Content-Type': 'application/json' },
        body: JSON.stringify({ images: [{ kind: 'furnace', dataUrl: tinyJpeg }] })
    });
    const response = await worker.fetch(request, { GEMINI_API_KEY: 'test-secret', ALLOWED_ORIGINS: 'https://example.github.io' });
    assert.equal(response.status, 403);
});
