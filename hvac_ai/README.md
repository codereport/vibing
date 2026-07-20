# HVAC Efficiency Pro — HCA Sales + Operations Tool

Single-file Ontario HVAC assessment prototype. Open `index.html` directly in a browser; no build step or API keys are required. It is optimized for iPad/phone field use and uses browser camera capture.

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
- Connect rating-plate photos to a secured vision/backend workflow. The prototype deliberately does not fabricate OCR values; the HCA must confirm every plate field.
- Validate rebate amounts and equipment eligibility against the live Home Renovation Savings rules at quote time.
- Configure the sales manager phone number on first use of the call button.
- Confirm the 5-inch media cabinet dimensions and front service/pull-out clearance from the selected product instructions. The 7.5-inch value is only a planning target, not a universal installation requirement.

## Estimate disclaimer

The generated report explains that projections are estimates rather than guaranteed savings. Final system sizing requires a CSA F280 / Manual J calculation, and operations must verify site conditions and manufacturer clearances before installation.
