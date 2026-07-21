const MODEL = 'gemini-3.1-flash-lite';
const GEMINI_URL = `https://generativelanguage.googleapis.com/v1beta/models/${MODEL}:generateContent`;
const MAX_REQUEST_BYTES = 12 * 1024 * 1024;
const MAX_TOTAL_IMAGE_BYTES = 8 * 1024 * 1024;
const MAX_IMAGE_BYTES = 3 * 1024 * 1024;
const MAX_IMAGES = 4;
const IMAGE_DATA_URL = /^data:(image\/(?:jpeg|png|webp));base64,([A-Za-z0-9+/=]+)$/;

const SYSTEM_PROMPT = `You inspect residential HVAC rating-plate photos. Extract only values visible on the plates.

Rules:
- Photos are labelled FURNACE or COOLING/OUTDOOR UNIT. Do not move values between equipment types.
- Model and serial must be transcribed exactly, using uppercase letters, digits, and hyphens.
- Never invent a value. Return null when unreadable or not present.
- inputBtu and outputBtu are high-fire values in BTU/h, not low-fire values.
- afue and efficiency are percentages/ratings as numbers without units.
- tons is nominal cooling capacity. You may decode standard model-number capacity codes (018=1.5, 024=2, 030=2.5, 036=3, 042=3.5, 048=4, 060=5), but explain that in notes.
- furnace.type must be gas_furnace, high_eff_gas, electric, or null.
- cooling.type must be ac, heat_pump, old_hp, or null.
- confidence is 0-100 for the equipment result. Reduce it for blur, glare, obstruction, or inference.
- plateText is a short transcription of the lines supporting the extracted values, not every regulatory line.
- Mention uncertainty, conflicting plates, or derived capacity in notes.
- A human must verify every result before it is used.`;

const nullableString = description => ({ type: 'STRING', nullable: true, description });
const nullableNumber = description => ({ type: 'NUMBER', nullable: true, description });

const EQUIPMENT_SCHEMA = {
    type: 'OBJECT',
    properties: {
        furnace: {
            type: 'OBJECT',
            nullable: true,
            properties: {
                model: nullableString('Exact furnace model number or null.'),
                serial: nullableString('Exact furnace serial number or null.'),
                inputBtu: nullableNumber('High-fire input capacity in BTU/h or null.'),
                outputBtu: nullableNumber('High-fire output capacity in BTU/h or null.'),
                afue: nullableNumber('AFUE percentage or null.'),
                type: nullableString('gas_furnace, high_eff_gas, electric, or null.'),
                confidence: nullableNumber('Confidence from 0 to 100.'),
                plateText: nullableString('Short supporting plate transcription.'),
                notes: nullableString('Uncertainty or derivation note.')
            },
            required: ['model', 'serial', 'inputBtu', 'outputBtu', 'afue', 'type', 'confidence', 'plateText', 'notes']
        },
        cooling: {
            type: 'OBJECT',
            nullable: true,
            properties: {
                model: nullableString('Exact outdoor-unit model number or null.'),
                serial: nullableString('Exact outdoor-unit serial number or null.'),
                tons: nullableNumber('Nominal cooling capacity in tons or null.'),
                efficiency: nullableNumber('SEER, SEER2, or EER shown on the plate, or null.'),
                type: nullableString('ac, heat_pump, old_hp, or null.'),
                confidence: nullableNumber('Confidence from 0 to 100.'),
                plateText: nullableString('Short supporting plate transcription.'),
                notes: nullableString('Uncertainty or derivation note.')
            },
            required: ['model', 'serial', 'tons', 'efficiency', 'type', 'confidence', 'plateText', 'notes']
        },
        warnings: {
            type: 'ARRAY',
            items: { type: 'STRING' },
            description: 'Important human-review warnings.'
        }
    },
    required: ['furnace', 'cooling', 'warnings']
};

function json(body, status = 200, origin = null) {
    const headers = {
        'Content-Type': 'application/json; charset=utf-8',
        'Cache-Control': 'no-store',
        'X-Content-Type-Options': 'nosniff'
    };
    if (origin) {
        headers['Access-Control-Allow-Origin'] = origin;
        headers.Vary = 'Origin';
    }
    return new Response(JSON.stringify(body), { status, headers });
}

function allowedOrigin(request, env) {
    const origin = request.headers.get('Origin');
    if (!origin) return null;
    const allowed = String(env.ALLOWED_ORIGINS || '')
        .split(',')
        .map(value => value.trim().replace(/\/$/, ''))
        .filter(Boolean);
    return allowed.includes(origin.replace(/\/$/, '')) ? origin : null;
}

function estimatedBase64Bytes(base64) {
    const padding = base64.endsWith('==') ? 2 : base64.endsWith('=') ? 1 : 0;
    return Math.floor(base64.length * 3 / 4) - padding;
}

export function validateImages(payload) {
    if (!payload || !Array.isArray(payload.images)) throw new Error('The request must include an images array.');
    if (!payload.images.length || payload.images.length > MAX_IMAGES) throw new Error('Attach between 1 and 4 rating-plate photos.');

    const counts = { furnace: 0, cooling: 0 };
    let totalBytes = 0;
    const images = payload.images.map((image, index) => {
        if (!image || !['furnace', 'cooling'].includes(image.kind)) throw new Error(`Image ${index + 1} has an invalid equipment type.`);
        counts[image.kind] += 1;
        if (counts[image.kind] > 2) throw new Error(`Only two ${image.kind} photos may be analyzed at once.`);
        const match = String(image.dataUrl || '').match(IMAGE_DATA_URL);
        if (!match) throw new Error(`Image ${index + 1} must be a JPEG, PNG, or WebP data URL.`);
        const size = estimatedBase64Bytes(match[2]);
        if (size > MAX_IMAGE_BYTES) throw new Error(`Image ${index + 1} is larger than 3 MB after preparation.`);
        totalBytes += size;
        return { kind: image.kind, mimeType: match[1], data: match[2] };
    });
    if (totalBytes > MAX_TOTAL_IMAGE_BYTES) throw new Error('The prepared images exceed the 8 MB combined limit.');
    return images;
}

function limitedText(value, max = 1500) {
    if (typeof value !== 'string') return null;
    const cleaned = value.trim();
    return cleaned ? cleaned.slice(0, max) : null;
}

function identifier(value) {
    const cleaned = limitedText(value, 64);
    if (!cleaned) return null;
    const normalized = cleaned.toUpperCase().replace(/[‐‑‒–—]/g, '-').replace(/[^A-Z0-9-]/g, '');
    return normalized.length >= 3 ? normalized.slice(0, 32) : null;
}

function rangedNumber(value, min, max) {
    if (value === null || value === undefined || value === '') return null;
    const number = Number(value);
    return Number.isFinite(number) && number >= min && number <= max ? number : null;
}

export function sanitizeGeminiResult(raw) {
    const furnace = raw && raw.furnace && typeof raw.furnace === 'object' ? raw.furnace : null;
    const cooling = raw && raw.cooling && typeof raw.cooling === 'object' ? raw.cooling : null;
    const furnaceTypes = new Set(['gas_furnace', 'high_eff_gas', 'electric']);
    const coolingTypes = new Set(['ac', 'heat_pump', 'old_hp']);
    return {
        furnace: furnace ? {
            model: identifier(furnace.model),
            serial: identifier(furnace.serial),
            inputBtu: rangedNumber(furnace.inputBtu, 20000, 200000),
            outputBtu: rangedNumber(furnace.outputBtu, 10000, 200000),
            afue: rangedNumber(furnace.afue, 40, 100),
            type: furnaceTypes.has(furnace.type) ? furnace.type : null,
            confidence: rangedNumber(furnace.confidence, 0, 100),
            plateText: limitedText(furnace.plateText),
            notes: limitedText(furnace.notes, 500)
        } : null,
        cooling: cooling ? {
            model: identifier(cooling.model),
            serial: identifier(cooling.serial),
            tons: rangedNumber(cooling.tons, 1, 10),
            efficiency: rangedNumber(cooling.efficiency, 5, 40),
            type: coolingTypes.has(cooling.type) ? cooling.type : null,
            confidence: rangedNumber(cooling.confidence, 0, 100),
            plateText: limitedText(cooling.plateText),
            notes: limitedText(cooling.notes, 500)
        } : null,
        warnings: Array.isArray(raw && raw.warnings)
            ? raw.warnings.map(value => limitedText(value, 240)).filter(Boolean).slice(0, 8)
            : []
    };
}

async function analyze(request, env, origin) {
    if (!env.GEMINI_API_KEY) return json({ error: 'The Worker is missing its GEMINI_API_KEY secret.' }, 503, origin);
    const contentType = request.headers.get('Content-Type') || '';
    if (!contentType.toLowerCase().startsWith('application/json')) return json({ error: 'Content-Type must be application/json.' }, 415, origin);
    const contentLength = Number(request.headers.get('Content-Length') || 0);
    if (contentLength > MAX_REQUEST_BYTES) return json({ error: 'The request is too large.' }, 413, origin);

    let payload;
    try {
        payload = await request.json();
    } catch {
        return json({ error: 'The request body is not valid JSON.' }, 400, origin);
    }

    let images;
    try {
        images = validateImages(payload);
    } catch (error) {
        return json({ error: error.message }, 400, origin);
    }

    const parts = [{ text: SYSTEM_PROMPT }];
    images.forEach((image, index) => {
        parts.push({ text: `PHOTO ${index + 1}: ${image.kind === 'furnace' ? 'FURNACE' : 'COOLING/OUTDOOR UNIT'} RATING PLATE` });
        parts.push({ inline_data: { mime_type: image.mimeType, data: image.data } });
    });

    let upstream;
    try {
        upstream = await fetch(GEMINI_URL, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'x-goog-api-key': env.GEMINI_API_KEY },
            body: JSON.stringify({
                contents: [{ role: 'user', parts }],
                generationConfig: {
                    temperature: 0,
                    maxOutputTokens: 1400,
                    responseMimeType: 'application/json',
                    responseSchema: EQUIPMENT_SCHEMA
                }
            })
        });
    } catch {
        return json({ error: 'Gemini could not be reached. Please retry.' }, 502, origin);
    }

    let upstreamBody;
    try {
        upstreamBody = await upstream.json();
    } catch {
        return json({ error: 'Gemini returned an unreadable response.' }, 502, origin);
    }
    if (!upstream.ok) {
        console.error(
            'Gemini request failed',
            upstream.status,
            upstreamBody && upstreamBody.error && upstreamBody.error.status,
            upstreamBody && upstreamBody.error && upstreamBody.error.message
        );
        const status = upstream.status === 429 ? 429 : 502;
        return json({ error: status === 429 ? 'Gemini is temporarily rate limited. Please retry shortly.' : 'Gemini could not analyze these photos.' }, status, origin);
    }

    const text = (upstreamBody.candidates?.[0]?.content?.parts || []).map(part => part.text || '').join('');
    if (!text) return json({ error: 'Gemini did not return an equipment result.' }, 502, origin);

    let parsed;
    try {
        parsed = JSON.parse(text);
    } catch {
        return json({ error: 'Gemini returned invalid structured data.' }, 502, origin);
    }
    return json({ ...sanitizeGeminiResult(parsed), model: MODEL, usage: upstreamBody.usageMetadata || null }, 200, origin);
}

export default {
    async fetch(request, env) {
        const url = new URL(request.url);
        const originHeader = request.headers.get('Origin');
        const origin = allowedOrigin(request, env);

        if (originHeader && !origin) return json({ error: 'This site is not allowed to use the analyzer.' }, 403);
        if (request.method === 'OPTIONS') {
            if (!origin) return new Response(null, { status: 403 });
            return new Response(null, {
                status: 204,
                headers: {
                    'Access-Control-Allow-Origin': origin,
                    'Access-Control-Allow-Methods': 'POST, OPTIONS',
                    'Access-Control-Allow-Headers': 'Content-Type',
                    'Access-Control-Max-Age': '86400',
                    Vary: 'Origin'
                }
            });
        }
        if (url.pathname === '/health' && request.method === 'GET') return json({ ok: true, model: MODEL }, 200, origin);
        if (url.pathname === '/analyze' && request.method === 'POST') return analyze(request, env, origin);
        return json({ error: 'Not found.' }, 404, origin);
    }
};
