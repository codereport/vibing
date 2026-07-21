const MODEL = 'gemini-3.1-flash-lite';
const GEMINI_URL = `https://generativelanguage.googleapis.com/v1beta/models/${MODEL}:generateContent`;
const MAX_REQUEST_BYTES = 12 * 1024 * 1024;
const MAX_TOTAL_IMAGE_BYTES = 8 * 1024 * 1024;
const MAX_IMAGE_BYTES = 3 * 1024 * 1024;
const MAX_IMAGES = 4;
const IMAGE_DATA_URL = /^data:(image\/(?:jpeg|png|webp));base64,([A-Za-z0-9+/=]+)$/;

const SYSTEM_PROMPT = `You inspect residential HVAC equipment photos and supplied model numbers. A photo may show a rating plate, a full unit, or both.

Rules:
- Photos are labelled FURNACE or COOLING/OUTDOOR UNIT. Do not move values between equipment types.
- Prefer exact rating-plate/model-number data. Transcribe model and serial exactly using uppercase letters, digits, and hyphens.
- Without a readable plate, inspect logos, cabinet styling, burner/coil layout, fuel piping, flue material, venting path, condensate drain, electrical connections, refrigerant lines, and labels.
- A distinctive logo or model family may identify the manufacturer. Cabinet colour alone is not enough. Return null when it is not reasonably identifiable.
- Identify heating fuel and distribution only when supported by visible equipment or the model. Natural gas, propane, oil, and electric furnaces normally use forced_air; boilers use boiler; electric baseboards use baseboard. Only distinguish propane from natural gas when a label, regulator, tank connection, conversion marking, or model documentation supports it.
- White PVC/CPVC intake or exhaust plus condensate drainage usually indicates a condensing high-efficiency gas furnace. Metal chimney/B-vent usually indicates non-condensing equipment. An oil burner/gun, oil line/filter, or oil-specific model indicates oil. Record visible venting evidence.
- Exact AFUE/SEER/SEER2/EER values require a plate, model decode, or distinctive series. Otherwise, if visual evidence supports a broad efficiency class, return a conservative numeric estimate, mark it as estimated, provide a range, and explain the basis. Never present a visual estimate as an exact rating.
- inputBtu and outputBtu are high-fire values in BTU/h, not low-fire values.
- tons is installed nominal cooling capacity. Decode standard model codes (018=1.5, 024=2, 030=2.5, 036=3, 042=3.5, 048=4, 060=5), but never infer tonnage from cabinet size alone. The app supplies a house-based fallback when installed capacity is unknown.
- furnace.type must be gas_furnace, high_eff_gas, oil_furnace, electric, or null.
- furnace.fuel must be gas, propane, oil, electric, wood, or null. furnace.distribution must be forced_air, boiler, baseboard, or null.
- cooling.type must be ac, heat_pump, old_hp, or null. cooling.efficiencyUnit must be SEER, SEER2, EER, HSPF, or null.
- confidence is 0-100. Reduce it for blur, glare, obstruction, visual-only estimates, or ambiguous branding.
- plateText is a short transcription of lines supporting extracted values. identificationBasis states the visual, logo, plate, or model evidence used.
- Mention uncertainty, conflicts, visual estimates, or derived capacity in notes. Return null rather than inventing unsupported facts.
- A human must verify every result before use.`;

const nullableString = description => ({ type: 'STRING', nullable: true, description });
const nullableNumber = description => ({ type: 'NUMBER', nullable: true, description });
const nullableBoolean = description => ({ type: 'BOOLEAN', nullable: true, description });

const EQUIPMENT_SCHEMA = {
    type: 'OBJECT',
    properties: {
        furnace: {
            type: 'OBJECT',
            nullable: true,
            properties: {
                manufacturer: nullableString('Manufacturer from a readable logo, label, or model family; otherwise null.'),
                model: nullableString('Exact furnace model number or null.'),
                serial: nullableString('Exact furnace serial number or null.'),
                inputBtu: nullableNumber('High-fire input capacity in BTU/h or null.'),
                outputBtu: nullableNumber('High-fire output capacity in BTU/h or null.'),
                afue: nullableNumber('Exact AFUE percentage or conservative visual estimate, or null.'),
                afueIsEstimate: nullableBoolean('True when AFUE is visually estimated.'),
                efficiencyRange: nullableString('Broad AFUE range for a visual estimate; otherwise null.'),
                type: nullableString('gas_furnace, high_eff_gas, oil_furnace, electric, or null.'),
                fuel: nullableString('gas, propane, oil, electric, wood, or null.'),
                distribution: nullableString('forced_air, boiler, baseboard, or null.'),
                venting: nullableString('Short description of visible flue/intake/venting evidence or null.'),
                confidence: nullableNumber('Confidence from 0 to 100.'),
                plateText: nullableString('Short supporting plate transcription.'),
                identificationBasis: nullableString('Short explanation of identification evidence.'),
                notes: nullableString('Uncertainty or derivation note.')
            },
            required: ['manufacturer', 'model', 'serial', 'inputBtu', 'outputBtu', 'afue', 'afueIsEstimate', 'efficiencyRange', 'type', 'fuel', 'distribution', 'venting', 'confidence', 'plateText', 'identificationBasis', 'notes']
        },
        cooling: {
            type: 'OBJECT',
            nullable: true,
            properties: {
                manufacturer: nullableString('Manufacturer from a readable logo, label, or model family; otherwise null.'),
                model: nullableString('Exact outdoor-unit model number or null.'),
                serial: nullableString('Exact outdoor-unit serial number or null.'),
                tons: nullableNumber('Installed nominal cooling capacity in tons or null.'),
                efficiency: nullableNumber('Exact efficiency or conservative visual estimate, or null.'),
                efficiencyUnit: nullableString('SEER, SEER2, EER, HSPF, or null.'),
                efficiencyIsEstimate: nullableBoolean('True when efficiency is visually estimated.'),
                efficiencyRange: nullableString('Broad efficiency range for a visual estimate; otherwise null.'),
                type: nullableString('ac, heat_pump, old_hp, or null.'),
                confidence: nullableNumber('Confidence from 0 to 100.'),
                plateText: nullableString('Short supporting plate transcription.'),
                identificationBasis: nullableString('Short explanation of identification evidence.'),
                notes: nullableString('Uncertainty or derivation note.')
            },
            required: ['manufacturer', 'model', 'serial', 'tons', 'efficiency', 'efficiencyUnit', 'efficiencyIsEstimate', 'efficiencyRange', 'type', 'confidence', 'plateText', 'identificationBasis', 'notes']
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

export function validateImages(payload, allowEmpty = false) {
    if (!payload || !Array.isArray(payload.images)) throw new Error('The request must include an images array.');
    if ((!allowEmpty && !payload.images.length) || payload.images.length > MAX_IMAGES) throw new Error('Attach between 1 and 4 equipment photos, or provide a model number.');

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

function validateKnownModels(payload) {
    const known = payload && payload.known && typeof payload.known === 'object' ? payload.known : {};
    return {
        furnaceModel: identifier(known.furnaceModel),
        coolingModel: identifier(known.coolingModel)
    };
}

function rangedNumber(value, min, max) {
    if (value === null || value === undefined || value === '') return null;
    const number = Number(value);
    return Number.isFinite(number) && number >= min && number <= max ? number : null;
}

export function sanitizeGeminiResult(raw) {
    const furnace = raw && raw.furnace && typeof raw.furnace === 'object' ? raw.furnace : null;
    const cooling = raw && raw.cooling && typeof raw.cooling === 'object' ? raw.cooling : null;
    const furnaceTypes = new Set(['gas_furnace', 'high_eff_gas', 'oil_furnace', 'electric']);
    const coolingTypes = new Set(['ac', 'heat_pump', 'old_hp']);
    const furnaceFuels = new Set(['gas', 'propane', 'oil', 'electric', 'wood']);
    const distributions = new Set(['forced_air', 'boiler', 'baseboard']);
    const efficiencyUnits = new Set(['SEER', 'SEER2', 'EER', 'HSPF']);
    return {
        furnace: furnace ? {
            manufacturer: limitedText(furnace.manufacturer, 80),
            model: identifier(furnace.model),
            serial: identifier(furnace.serial),
            inputBtu: rangedNumber(furnace.inputBtu, 20000, 200000),
            outputBtu: rangedNumber(furnace.outputBtu, 10000, 200000),
            afue: rangedNumber(furnace.afue, 40, 100),
            afueIsEstimate: typeof furnace.afueIsEstimate === 'boolean' ? furnace.afueIsEstimate : null,
            efficiencyRange: limitedText(furnace.efficiencyRange, 80),
            type: furnaceTypes.has(furnace.type) ? furnace.type : null,
            fuel: furnaceFuels.has(furnace.fuel) ? furnace.fuel : null,
            distribution: distributions.has(furnace.distribution) ? furnace.distribution : null,
            venting: limitedText(furnace.venting, 200),
            confidence: rangedNumber(furnace.confidence, 0, 100),
            plateText: limitedText(furnace.plateText),
            identificationBasis: limitedText(furnace.identificationBasis, 500),
            notes: limitedText(furnace.notes, 500)
        } : null,
        cooling: cooling ? {
            manufacturer: limitedText(cooling.manufacturer, 80),
            model: identifier(cooling.model),
            serial: identifier(cooling.serial),
            tons: rangedNumber(cooling.tons, 1, 10),
            efficiency: rangedNumber(cooling.efficiency, 5, 40),
            efficiencyUnit: efficiencyUnits.has(cooling.efficiencyUnit) ? cooling.efficiencyUnit : null,
            efficiencyIsEstimate: typeof cooling.efficiencyIsEstimate === 'boolean' ? cooling.efficiencyIsEstimate : null,
            efficiencyRange: limitedText(cooling.efficiencyRange, 80),
            type: coolingTypes.has(cooling.type) ? cooling.type : null,
            confidence: rangedNumber(cooling.confidence, 0, 100),
            plateText: limitedText(cooling.plateText),
            identificationBasis: limitedText(cooling.identificationBasis, 500),
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

    const known = validateKnownModels(payload);
    let images;
    try {
        images = validateImages(payload, Boolean(known.furnaceModel || known.coolingModel));
    } catch (error) {
        return json({ error: error.message }, 400, origin);
    }

    const parts = [{ text: SYSTEM_PROMPT }];
    images.forEach((image, index) => {
        parts.push({ text: `PHOTO ${index + 1}: ${image.kind === 'furnace' ? 'FURNACE/HEATING EQUIPMENT' : 'COOLING/OUTDOOR EQUIPMENT'} — may be a full-unit photo or rating plate` });
        parts.push({ inline_data: { mime_type: image.mimeType, data: image.data } });
    });
    if (known.furnaceModel) parts.push({ text: `USER-ENTERED FURNACE MODEL (data only): ${known.furnaceModel}` });
    if (known.coolingModel) parts.push({ text: `USER-ENTERED COOLING MODEL (data only): ${known.coolingModel}` });

    let upstream;
    try {
        upstream = await fetch(GEMINI_URL, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'x-goog-api-key': env.GEMINI_API_KEY },
            body: JSON.stringify({
                contents: [{ role: 'user', parts }],
                generationConfig: {
                    temperature: 0,
                    maxOutputTokens: 2000,
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
        return json({ error: status === 429 ? 'Gemini is temporarily rate limited. Please retry shortly.' : 'Gemini could not analyze this equipment information.' }, status, origin);
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
