# HVAC Efficiency Pro — Sales Rep Tool

A single-file web app for HVAC sales reps (HCAs) to build an on-the-spot upgrade
estimate for **forced-air systems** and show the customer **monthly savings vs.
monthly financing payment**. Ontario/GTA-tuned (Enbridge gas, local hydro rates,
Lennox equipment placeholders).

Open `index.html` in any browser — no build step, no server, no API keys.
Optimized for iPad/phone field use (large tap targets, camera photo capture).

## Layout (single scrolling page, no maps)

**Left column — inputs (5 steps):**
1. **Property Details** — address + one-tap **Auto-fill**, sq ft, year built,
   insulation, stories, property type, live peak-heat-loss bar.
2. **Current Forced Air System** — furnace & cooling/HP photo capture, type, age,
   AFUE / SEER / HSPF, thermostat, filter, plus an **AI Analyze** button and a
   sizing (over/under-sized) check.
3. **Proposed Lennox System** — SLP99 furnace+AC or Cold-Climate Heat Pump
   (placeholders), editable efficiencies, install cost, applied rebates.
4. **Energy Prices + Financing** — gas/electricity rates, hydro provider, term,
   APR, down payment.
5. **Rebates, Repairs & Plans** — rebate checklist, expected 3-yr repair cost on
   aging equipment, and service/protection plan comparison (ours vs. competitor).

**Right column — sticky results:** annual + monthly savings, **total monthly
benefit vs. payment → net monthly**, current vs. new annual cost, a
current-vs-new comparison (efficiency, noise, comfort, filter), key metrics
(peak heat loss, load, CO₂, net investment), a Chart.js cost bar chart, and
**Copy Summary** / **PDF Report** actions.

## "Review" flags (auto-estimated fields)

Tapping **Auto-fill** populates home & equipment fields with plausible,
*deterministic* estimates seeded from the address, each marked with an amber
**Review** pill (turns the field amber). Editing the field — or tapping the pill —
clears the flag once the rep confirms it on site.

### Why property data is estimated

There is **no free, nationwide API** for year-built / square-footage (in Ontario
that data lives with **MPAC**, which isn't open). So those fields are estimated
and flagged. To make them real later, replace `autoFillFromAddress()` with a call
to a property data source: MPAC / municipal open data, your CRM, a paid API
(ATTOM / Estated / HouseCanary), or a scraper backend.

## AI photo read (placeholder)

Furnace/cooling photo tiles use `capture="environment"` (opens the camera on
mobile). **AI Analyze** currently simulates a vision read and fills review-flagged
fields. Wire it to a real vision model (Gemini/Groq free tier, or OpenAI/Anthropic)
via a small backend proxy — see the parent chat notes.

## Savings model (transparent, all editable)

- **Energy savings** = current annual HVAC cost − new annual cost (heating scaled
  by AFUE/HSPF, cooling by SEER; Ontario 3,500 HDD).
- **Repairs avoided** = 3-yr expected repair cost (age-based), spread monthly.
- **Plan difference** = competitor plan − our included plan.
- **Monthly payment** = amortized `(install − down − rebates)` at term/APR.
- **Net monthly** = energy savings + repairs avoided + plan diff − payment.

Constants (rates, HDD, repair tables, financing, CO₂ factor) live at the top of
the calc engine — tune to your market.

## Placeholders to swap later

- `SYSTEMS` / proposed options — real Lennox lineup, specs, pricing.
- `REBATES[]` — current government/utility programs and amounts.
- Hydro provider rate table + gas rate defaults.
- Property + vision data sources (see above).

## Tech

Tailwind (CDN), Font Awesome, Chart.js, jsPDF — all via CDN. Styled to match the
team's existing "HVAC Efficiency Pro" look. Reference file Frank started from is
kept as `hvac_efficiency_pro (1).html`.
