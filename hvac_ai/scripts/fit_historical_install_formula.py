#!/usr/bin/env python3
"""Decode installed HVAC capacities and fit a square-footage benchmark.

This analysis intentionally predicts the nominal equipment found on invoices.
It does not estimate a home's CSA F280 heat loss or heat gain. Toronto permit
data supplies residential gross floor area, but it does not supply measured
airtightness, insulation, windows, orientation, or duct/system zoning.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
import statistics
from pathlib import Path


COOLING_CODE_TO_TONS = {
    "018": 1.5,
    "024": 2.0,
    "030": 2.5,
    "036": 3.0,
    "042": 3.5,
    "048": 4.0,
    "060": 5.0,
}

# Model-number decoding references include the manufacturers' nomenclature and
# specification tables:
# - Lennox ML14XC1: https://www.lennox.com/dA/54a433c46e/corp1502b.pdf
# - Lennox EL297: https://www.lennox.com/dA/e2796b4d92/100088.pdf
# - Goodman GRVT96: https://apps.goodmanmfg.com/brochures/files/68ee63f710d60SS-GRVT96_GDVT96-R32.pdf
# - York TM9Y: https://www.york.com/Residential-Equipment/Heating-and-Cooling/Gas-Furnaces/tm9y_ds/tm9y-96-afue-two-stage-furnace

COOLING_PATTERNS = (
    re.compile(
        r"(?:ML14XC1S?|EL16XC1S?|EL18XCVS?)-?"
        r"(018|024|030|036|042|048|060)",
        re.I,
    ),
    re.compile(
        r"(?:GLXS\d|ALXS\d)[A-Z]{2}(18|24|30|36|42|48|60)10", re.I
    ),
    re.compile(r"YCG(18|24|30|36|42|48|60)", re.I),
)

FURNACE_PATTERNS = (
    re.compile(r"(?:EL297|ML296|ML196|SLP99)UH(045|070|090|110|135)", re.I),
    re.compile(r"GR(?:9S|VT)96(040|060|080|100|120)", re.I),
    re.compile(r"TM9[VEY](040|060|080|100|120)", re.I),
)


def decode_cooling_tons(model: str) -> float | None:
    """Return nominal tons encoded in one of the observed A/C model families."""
    normalized = re.sub(r"\s+", "", model.upper())
    for pattern in COOLING_PATTERNS:
        match = pattern.search(normalized)
        if match:
            code = match.group(1)
            if len(code) == 2:
                code = "0" + code
            return COOLING_CODE_TO_TONS[code]
    return None


def decode_furnace_input_btu(model: str) -> int | None:
    """Return nominal furnace input BTU/h encoded in an observed model number."""
    normalized = re.sub(r"\s+", "", model.upper())
    for pattern in FURNACE_PATTERNS:
        match = pattern.search(normalized)
        if match:
            return int(match.group(1)) * 1000
    return None


def linear_fit(points: list[tuple[float, float]]) -> dict[str, float | int]:
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    mean_x = statistics.mean(xs)
    mean_y = statistics.mean(ys)
    denominator = sum((value - mean_x) ** 2 for value in xs)
    slope = sum((x - mean_x) * (y - mean_y) for x, y in points) / denominator
    intercept = mean_y - slope * mean_x
    predictions = [intercept + slope * x for x in xs]
    residual_ss = sum((actual - predicted) ** 2 for actual, predicted in zip(ys, predictions))
    total_ss = sum((actual - mean_y) ** 2 for actual in ys)
    return {
        "n": len(points),
        "intercept": intercept,
        "sqft_coefficient": slope,
        "r_squared": 1 - residual_ss / total_ss if total_ss else 0.0,
        "mae": statistics.mean(abs(actual - predicted) for actual, predicted in zip(ys, predictions)),
        "rmse": math.sqrt(residual_ss / len(points)),
    }


def leave_one_out_mae(points: list[tuple[float, float]]) -> float:
    errors: list[float] = []
    for index, (sqft, actual) in enumerate(points):
        training = points[:index] + points[index + 1 :]
        fit = linear_fit(training)
        predicted = float(fit["intercept"]) + float(fit["sqft_coefficient"]) * sqft
        errors.append(abs(actual - predicted))
    return statistics.mean(errors)


def decode_unique(models: list[str], decoder) -> tuple[str, float | None, list[float]]:
    values = sorted({value for model in models if (value := decoder(model)) is not None})
    if not values:
        return "missing_or_unrecognized_model", None, []
    if len(values) > 1:
        return "ambiguous_multiple_capacities", None, values
    return "usable", values[0], values


def analyze(input_path: Path, audit_path: Path, report_path: Path) -> dict:
    with input_path.open(newline="", encoding="utf-8-sig") as source:
        rows = list(csv.DictReader(source))

    furnace_points: list[tuple[float, float]] = []
    cooling_points: list[tuple[float, float]] = []
    audit_rows: list[dict[str, str]] = []
    counts = {
        "furnace": {"eligible": 0, "usable": 0, "missing_or_unrecognized_model": 0, "ambiguous_multiple_capacities": 0},
        "cooling": {"eligible": 0, "usable": 0, "missing_or_unrecognized_model": 0, "ambiguous_multiple_capacities": 0},
    }

    for row in rows:
        sqft = float(row["residential_gfa_sqft"])
        models = [value for value in row["recognized_equipment_models"].split(";") if value]
        has_furnace = "furnace" in row["equipment"].split(";")
        has_cooling = "air_conditioner" in row["equipment"].split(";")

        furnace_status, furnace_btu, furnace_values = ("not_applicable", None, [])
        cooling_status, cooling_tons, cooling_values = ("not_applicable", None, [])
        if has_furnace:
            counts["furnace"]["eligible"] += 1
            furnace_status, furnace_btu, furnace_values = decode_unique(models, decode_furnace_input_btu)
            counts["furnace"][furnace_status] += 1
            if furnace_status == "usable":
                furnace_points.append((sqft, float(furnace_btu)))
        if has_cooling:
            counts["cooling"]["eligible"] += 1
            cooling_status, cooling_tons, cooling_values = decode_unique(models, decode_cooling_tons)
            counts["cooling"][cooling_status] += 1
            if cooling_status == "usable":
                cooling_points.append((sqft, float(cooling_tons)))

        audit_rows.append(
            {
                "invoice_address": row["invoice_address"],
                "residential_gfa_sqft": row["residential_gfa_sqft"],
                "permit_num": row["permit_num"],
                "equipment": row["equipment"],
                "recognized_equipment_models": row["recognized_equipment_models"],
                "furnace_decode_status": furnace_status,
                "furnace_input_btu": "" if furnace_btu is None else str(int(furnace_btu)),
                "furnace_decoded_values": ";".join(str(int(value)) for value in furnace_values),
                "cooling_decode_status": cooling_status,
                "cooling_tons": "" if cooling_tons is None else str(cooling_tons),
                "cooling_decoded_values": ";".join(str(value) for value in cooling_values),
            }
        )

    audit_path.parent.mkdir(parents=True, exist_ok=True)
    with audit_path.open("w", newline="", encoding="utf-8") as destination:
        writer = csv.DictWriter(destination, fieldnames=list(audit_rows[0]))
        writer.writeheader()
        writer.writerows(audit_rows)

    furnace_fit = linear_fit(furnace_points)
    cooling_fit = linear_fit(cooling_points)
    furnace_fit["leave_one_out_mae"] = leave_one_out_mae(furnace_points)
    cooling_fit["leave_one_out_mae"] = leave_one_out_mae(cooling_points)
    report = {
        "source_candidates": len(rows),
        "capacity_decode_counts": counts,
        "formula": {
            "furnace_input_btu": furnace_fit,
            "cooling_tons": cooling_fit,
        },
        "limitations": [
            "The target is historical installed nameplate capacity, not CSA F280 design load.",
            "Permit residential GFA may not equal current conditioned floor area.",
            "The source does not contain measured envelope, window, orientation, duct, zoning, or occupancy fields.",
            "Rows with missing models or more than one decoded capacity are excluded from fitting.",
        ],
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "input",
        nargs="?",
        type=Path,
        default=Path("output/toronto_permit_match/plausible_single_home_training_candidates.csv"),
    )
    parser.add_argument(
        "--audit",
        type=Path,
        default=Path("output/historical_install_formula/capacity_audit.csv"),
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=Path("output/historical_install_formula/formula_report.json"),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.input.is_file():
        raise SystemExit(f"Input not found: {args.input}")
    report = analyze(args.input, args.audit, args.report)
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
