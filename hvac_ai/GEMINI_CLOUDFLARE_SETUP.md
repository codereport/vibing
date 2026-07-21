# Gemini + Cloudflare Worker setup

The two browser apps call one Cloudflare Worker. The Worker holds the Gemini key, validates and resizes the request, uses a fixed extraction prompt, and returns only sanitized structured fields. The Gemini key must never be added to `config.js`, either HTML file, or GitHub.

## What is already wired

- `hvac-efficiency-pro-hca.html` and `hvac-efficiency-pro-customer.html` send up to two furnace and two cooling rating-plate photos.
- The browser resizes each image to a maximum 1,800-pixel edge, converts it to JPEG, and thereby strips normal image metadata before upload.
- `worker/src/index.js` calls `gemini-3.1-flash-lite` and accepts only a fixed JSON schema.
- Model numbers, serial numbers, capacities, efficiencies, equipment types, notes, and confidence are validated before they return to the browser.
- AI-filled fields stay amber and the HCA verification checkbox is reset. AI output is never treated as verified sizing data.
- `config.js` contains only the public Worker URL. No secret belongs there.

## 1. Create the Gemini API key

1. Sign in at [Google AI Studio API Keys](https://aistudio.google.com/apikey).
2. Create or select a dedicated Google Cloud project for this app.
3. Click **Create API key** and create a new authorization key. New AI Studio keys are authorization keys by default as of July 2026.
4. Copy the key somewhere temporary. Do not paste it into any repository file.
5. In AI Studio, confirm the key is restricted to the Gemini API. If it is an older unrestricted standard key, replace it with a new authorization key.
6. For real customer photos, enable the Gemini paid tier and configure a Google Cloud budget alert. The paid tier currently marks submitted data as not used to improve Google's products; the free tier does not. Google may still retain prompts/context/output for 55 days for abuse monitoring.

The configured model is `gemini-3.1-flash-lite`. Current paid standard pricing is $0.25 per million text/image/video input tokens and $1.50 per million output tokens. Image token usage depends on image dimensions, so use the Google usage dashboard to establish the real per-analysis cost from your first 50–100 jobs.

## 2. Create and deploy the Cloudflare Worker

Install Node.js 20 or newer, then run these commands from this repository:

```bash
cd worker
npm install
npx wrangler login
```

Open `worker/wrangler.jsonc` and replace `YOUR-GITHUB-USERNAME` with the GitHub account or organization that hosts the Pages site. For a normal project Pages URL such as `https://acmehvac.github.io/hvac_ai/`, the browser origin is only:

```text
https://acmehvac.github.io
```

If the site uses a custom domain, add that exact origin after a comma. Do not include paths or trailing slashes.

Store the Gemini key as an encrypted Worker secret:

```bash
npx wrangler secret put GEMINI_API_KEY
```

Paste the Gemini key only when Wrangler prompts for it. Then deploy:

```bash
npm run deploy
```

Wrangler prints a URL similar to:

```text
https://hvac-equipment-analyzer.YOUR-SUBDOMAIN.workers.dev
```

Confirm the Worker is alive by opening:

```text
https://hvac-equipment-analyzer.YOUR-SUBDOMAIN.workers.dev/health
```

The expected response is:

```json
{"ok":true,"model":"gemini-3.1-flash-lite"}
```

## 3. Connect the GitHub Pages apps

Open `config.js` and replace the production placeholder with your Worker URL, keeping `/analyze`:

```js
aiAnalyzeEndpoint: isLocal
    ? 'http://localhost:8787/analyze'
    : 'https://hvac-equipment-analyzer.YOUR-SUBDOMAIN.workers.dev/analyze',
```

Commit and push the site files to GitHub Pages. The key remains safe because GitHub receives only the public Worker address.

Test from the deployed site:

1. Open the HCA app from the landing page.
2. Add a clear, square-on furnace or outdoor-unit rating-plate photo.
3. Click **AI Analyze**.
4. Confirm model/serial/capacity against the actual plate before checking the HCA verification box.
5. Repeat with glare, blur, and multiple plates to verify the app reports uncertainty rather than silently accepting poor data.

## 4. Test locally before deployment

In one terminal:

```bash
cd worker
cp .dev.vars.example .dev.vars
```

Edit `worker/.dev.vars` and put the real key after `GEMINI_API_KEY=`. This file is git-ignored. Then run:

```bash
npm install
npm run dev
```

In a second terminal, from the repository root:

```bash
python3 -m http.server 8000
```

Open `http://localhost:8000/`. `config.js` automatically uses `http://localhost:8787/analyze` on localhost, and the supplied Worker configuration already allows `http://localhost:8000`.

## 5. Production safety checklist

- Use the Gemini paid tier for actual customer images, obtain appropriate customer consent, and avoid sending faces, addresses, invoices, or other unrelated personal information.
- Keep `GEMINI_API_KEY` only in Cloudflare secrets. If it ever appears in Git or browser code, rotate it immediately.
- Configure Google Cloud budget alerts and review Gemini usage regularly.
- Restrict `ALLOWED_ORIGINS` to the production Pages origin and any real custom domain. Remove localhost when local testing is finished if desired.
- The Worker sets image-count, type, per-image, total-image, and request-size limits. It does not store images or responses and sends `Cache-Control: no-store`.
- CORS is not authentication: a determined caller can forge an origin outside a browser. Before a broad public customer launch, add Cloudflare Turnstile and/or an account-level rate-limit rule. For a controlled pilot, monitor Worker and Gemini usage daily.
- Cloudflare Workers Free currently includes 100,000 requests/day but only 10 ms CPU per invocation. This small proxy should usually fit, and time waiting for Gemini is not CPU time. If it hits CPU limits, Workers Paid starts at $5 USD/month.
- Never rely on AI output for final CSA F280/Manual J sizing, safety decisions, warranty eligibility, or installation instructions. Verify the plate and manufacturer documentation.

## Troubleshooting

- **“AI Analyze is not configured yet”**: replace the production placeholder in `config.js`.
- **403 / site not allowed**: the exact browser origin is missing from `ALLOWED_ORIGINS`; edit `worker/wrangler.jsonc` and redeploy.
- **Worker missing `GEMINI_API_KEY`**: run `npx wrangler secret put GEMINI_API_KEY` from `worker/`, then redeploy if requested.
- **429**: Gemini quota/rate limit was reached. Check the Gemini dashboard and paid-tier status, then retry later.
- **413 / image too large**: use fewer photos or crop closer to the plate. The browser normally compresses photos below the Worker limit.
- **Cloudflare CPU-limit error**: move the Worker to the $5/month paid plan and inspect Worker logs with `npm run tail`.
- **Poor recognition**: photograph the plate square-on, fill the frame, avoid flash glare, and take a second close-up. Always verify amber fields.

## Useful commands

```bash
cd worker
npm test
npm run deploy
npm run tail
npx wrangler secret list
```
