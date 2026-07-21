#!/usr/bin/env python3
"""Plot decoded HVAC nameplate capacity against permit gross floor area."""

from __future__ import annotations

import argparse
import csv
import json
import statistics
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


def load_usable_points(audit_path: Path, equipment: str, value_column: str):
    with audit_path.open(newline="", encoding="utf-8") as source:
        rows = list(csv.DictReader(source))
    points = [
        (float(row["residential_gfa_sqft"]), float(row[value_column]))
        for row in rows
        if row[f"{equipment}_decode_status"] == "usable"
    ]
    return rows, points


def add_panel(
    axis,
    points,
    fit,
    title: str,
    ylabel: str,
    color: str,
    unit: str,
):
    square_feet = np.array([point[0] for point in points])
    capacities = np.array([point[1] for point in points])
    x_line = np.linspace(square_feet.min(), square_feet.max(), 200)
    y_line = fit["intercept"] + fit["sqft_coefficient"] * x_line

    axis.scatter(
        square_feet,
        capacities,
        s=54,
        color=color,
        alpha=0.72,
        edgecolor="white",
        linewidth=0.7,
        zorder=3,
    )
    axis.plot(x_line, y_line, color="#111827", linewidth=2.2, label="Linear fit")
    axis.axhline(
        statistics.median(capacities),
        color="#64748b",
        linewidth=1.3,
        linestyle=(0, (3, 3)),
        label="Sample median",
    )
    axis.set_title(title, loc="left", fontsize=14, fontweight="bold", pad=11)
    axis.set_xlabel("Permit residential GFA (sq ft)")
    axis.set_ylabel(ylabel)
    axis.grid(True, color="#e2e8f0", linewidth=0.8)
    axis.set_axisbelow(True)
    axis.legend(frameon=False, loc="upper left")
    axis.text(
        0.98,
        0.96,
        f"n = {fit['n']}\nR² = {fit['r_squared']:.4f}\nLOOCV MAE = {fit['leave_one_out_mae']:.2f} {unit}",
        transform=axis.transAxes,
        horizontalalignment="right",
        verticalalignment="top",
        fontsize=10,
        bbox={"boxstyle": "round,pad=0.5", "facecolor": "white", "edgecolor": "#cbd5e1", "alpha": 0.94},
    )
    axis.spines[["top", "right"]].set_visible(False)


def plot(audit_path: Path, report_path: Path, output_path: Path) -> None:
    furnace_rows, furnace_points = load_usable_points(
        audit_path, "furnace", "furnace_input_btu"
    )
    cooling_rows, cooling_points = load_usable_points(
        audit_path, "cooling", "cooling_tons"
    )
    report = json.loads(report_path.read_text(encoding="utf-8"))

    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "axes.labelcolor": "#334155",
            "xtick.color": "#475569",
            "ytick.color": "#475569",
        }
    )
    figure, axes = plt.subplots(1, 2, figsize=(14, 7.2), constrained_layout=False)
    figure.patch.set_facecolor("#f8fafc")
    figure.subplots_adjust(left=0.07, right=0.985, bottom=0.15, top=0.79, wspace=0.11)
    for axis in axes:
        axis.set_facecolor("white")

    add_panel(
        axes[0],
        furnace_points,
        report["formula"]["furnace_input_btu"],
        "Furnace nameplate input",
        "Nominal furnace input (BTU/h)",
        "#f97316",
        "BTU/h",
    )
    axes[0].ticklabel_format(axis="y", style="plain")
    add_panel(
        axes[1],
        cooling_points,
        report["formula"]["cooling_tons"],
        "A/C nameplate capacity",
        "Nominal cooling capacity (tons)",
        "#0ea5e9",
        "tons",
    )

    source_count = report["source_candidates"]
    counts = report["capacity_decode_counts"]
    figure.suptitle(
        "Installed HVAC capacity versus permit square footage",
        fontsize=19,
        fontweight="bold",
        x=0.03,
        y=0.975,
        horizontalalignment="left",
    )
    figure.text(
        0.03,
        0.905,
        (
            f"{source_count} corrected permit-matched homes • "
            f"furnace: {len(furnace_points)} usable, {counts['furnace']['eligible'] - len(furnace_points)} excluded • "
            f"A/C: {len(cooling_points)} usable, {counts['cooling']['eligible'] - len(cooling_points)} excluded"
        ),
        fontsize=11,
        color="#475569",
    )
    figure.text(
        0.03,
        0.035,
        "Installed nameplate capacity is not a CSA F280 load calculation. Permit residential GFA may differ from current conditioned floor area.",
        fontsize=9.5,
        color="#64748b",
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output_path, dpi=180, facecolor=figure.get_facecolor())
    plt.close(figure)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
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
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("output/historical_install_formula/capacity_vs_square_footage.png"),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    plot(args.audit, args.report, args.output)
    print(f"Wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
