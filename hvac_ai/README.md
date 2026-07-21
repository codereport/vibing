# HVAC Efficiency Pro — HCA and Customer Apps

Static Ontario HVAC assessment prototype with separate HCA and customer versions. `index.html` is the landing page. The apps are optimized for iPad/phone field use and browser camera capture.

## Updated workflow

1. Property details: debounced/cancellable Ontario address search, second-source Canadian postal-code cross-check, address-assisted property type, documented square-footage source, heating distribution type, and preliminary heat loss plus heat gain in BTU/h and tons.
2. Current equipment: separate unit/rating-plate fields, filter and thermostat photos, current capacity matching, and explicit HCA confirmation.
3. Rebates, repairs and plan: HRS heat-pump incentive only, based on tonnage and fuel/meter eligibility; separate age-based furnace and cooling repair risks; routine maintenance excluded; current customer plan entered by the HCA.
4. Proposed equipment: three manufacturer-neutral packages—Optimum Furnace, Optimum System Heat Pump and Basic Heat Pump. Only the first two use communicating controls; Basic Heat Pump uses ecobee.
5. Energy and financing: geography/weather proxy, entered utility prices, oversizing/cycling adjustment, heat-pump fuel switching, equipment-specific avoided repairs, current plan and automatically selected lowest monthly payment term.
6. Customer view: concise projected monthly benefit and comfort/noise/air-quality/thermostat expectations. Comparison metrics and reconciliation live in the separate Savings Details view.
7. Post-agreement operations handoff: electrical panel, outdoor/indoor wide photos, line-set length, plenums/return, media-filter space, mounting and wall construction, notes, placement concept and an internal PDF.

## Important production integrations

- Replace the free address estimate with licensed MPAC/propertyline or approved CRM/property data. Exact Ontario residential square-footage data is not exposed by the current free geocoder.
- Replace the geography proxy with weather-normal data for the exact address and, where available, interval utility history.
- Deploy and configure the included Cloudflare Worker before using AI Analyze. It calls Gemini 2.5 Flash-Lite without exposing the key and leaves all returned plate fields unverified. See `GEMINI_CLOUDFLARE_SETUP.md`.
- Validate rebate amounts and equipment eligibility against the live Home Renovation Savings rules at quote time.
- Configure the sales manager phone number on first use of the call button.
- Confirm the 5-inch media cabinet dimensions and front service/pull-out clearance from the selected product instructions. The 7.5-inch value is only a planning target, not a universal installation requirement.

## Estimate disclaimer

The generated report explains that projections are estimates rather than guaranteed savings. Final system sizing requires a CSA F280 / Manual J calculation, and operations must verify site conditions and manufacturer clearances before installation.

## Toronto permit-data coverage audit

`scripts/match_invoice_addresses_to_toronto_permits.py` checks how many invoice
locations with a furnace or central-air installation can be matched to Toronto's
active and cleared building-permit datasets. It uses only the Python standard
library and caches the downloaded municipal CSV files locally.

```bash
python scripts/match_invoice_addresses_to_toronto_permits.py \
  "Invoice Items Report_Dated 07_01_24 - 07_20_26 full.xlsx"
```

Results are written under `output/toronto_permit_match/`. Customer addresses,
the input workbook, and downloaded datasets are git-ignored. A permit's
residential GFA is the area associated with the permitted work and is not
automatically the home's total square footage; the output keeps that distinction
explicit.

## Historical installed-size benchmark

The initial 92-row permit subset contained eight false-positive properties whose
only "furnace" model was a Bradford White `RG1PV`/`RG2PV` power-vent water
heater. The corrected equipment filter leaves 84 candidate homes. Recreate the
capacity audit and regression report with:

```bash
python scripts/fit_historical_install_formula.py
python scripts/plot_historical_install_formula.py
```

The script decodes nominal capacity from the observed Lennox, Goodman/Amana and
York model families, rejects missing or conflicting model capacities, and writes
an address-level audit plus JSON report under
`output/historical_install_formula/`. The plotting command writes
`capacity_vs_square_footage.png` in the same directory. The fitted equations
use 44 furnace and 56 A/C observations:

- furnace input BTU/h = `83,992.23 + 0.37958 × square feet`
- nominal A/C tons = `2.18061 + 0.00021622 × square feet`

The fits are extremely weak (`R² = 0.0004` for furnaces and `0.0594` for A/C).
The historical analysis is retained only as an installed-size benchmark report;
it is not exposed as a sizing option in either app. It does not replace the load
estimate used for energy projections.
The permit data has no measured envelope, window, orientation, duct or zoning
fields, so it cannot support an envelope-trained load formula. Final sizing
still requires CSA F280.
