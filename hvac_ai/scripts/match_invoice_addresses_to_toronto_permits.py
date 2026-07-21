#!/usr/bin/env python3
"""Match furnace/A/C invoice locations to Toronto's open permit datasets.

The script deliberately uses only Python's standard library. It:

1. streams the first worksheet in the ServiceTitan-style XLSX report;
2. keeps only locations with a furnace or central-air installation marker/model;
3. limits the municipal comparison to City of Toronto locations;
4. downloads/caches Toronto active and cleared building-permit CSV files;
5. matches normalized civic addresses; and
6. reports permit coverage and residential GFA candidates.

Residential GFA in the permit data is the area associated with the permitted
work. It is not automatically the home's total floor area. Only new-building
records are marked as plausible whole-building values, and even those require
validation before model training.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import time
import unicodedata
import urllib.request
import zipfile
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Iterator
from xml.etree import ElementTree as ET


XLSX_NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
SQM_TO_SQFT = 10.7639104167

TORONTO_DATASETS = (
    (
        "active",
        "https://ckan0.cf.opendata.inter.prod-toronto.ca/dataset/"
        "108c2bd1-6945-46f6-af92-02f5658ee7f7/resource/"
        "dfce3b7b-4f17-4a9d-9155-5e390a5ffa97/download/"
        "building-permits-active-permits.csv",
    ),
    (
        "cleared_since_2017",
        "https://ckan0.cf.opendata.inter.prod-toronto.ca/dataset/"
        "9e42a85b-180f-4dc5-b0d7-d46661a6c0ec/resource/"
        "b41c3e9e-4d2d-4b09-a789-9569d8da407c/download/"
        "cleared-building-permits-since-2017.csv",
    ),
    (
        "cleared_2000_2016",
        "https://ckan0.cf.opendata.inter.prod-toronto.ca/dataset/"
        "9e42a85b-180f-4dc5-b0d7-d46661a6c0ec/resource/"
        "c647bdae-0127-425e-86e6-2d88ff0e2adf/download/"
        "export_202507081211.csv",
    ),
)

FURNACE_MARKER_RE = re.compile(
    r"(?:MATERIAL\s+BURDEN\s+FURN(?:ACE)?\b|\bMT-FU-|\bLA-ON-FU\b)", re.I
)
AC_MARKER_RE = re.compile(
    r"(?:MATERIAL\s+BURDEN\s+AC\b|\bMT-AC-|\bLA-ON-AC\b)", re.I
)

# High-precision model-family patterns found in the supplied workbook. Keep
# this list deliberately conservative: heat-pump-only and ductless families
# are not classified as central A/C.
FURNACE_MODEL_RE = re.compile(
    r"(?:"
    r"\b(?:EL|ML)\d{3}UH[A-Z0-9-]*\b|"
    r"\bSLP(?:98|99)UH[A-Z0-9-]*\b|"
    r"\b(?:GM|GC|DM|DC|AM)(?:9|V)[A-Z0-9-]{5,}\b|"
    r"\bGR(?:9|V)[A-Z0-9-]{5,}\b|"
    r"\bTM[89][A-Z][A-Z0-9-]{5,}\b|"
    r"\b59[A-Z0-9-]{6,}\b|"
    r"\b(?:N|F)9\d[A-Z0-9-]{5,}\b"
    r")",
    re.I,
)
AC_MODEL_RE = re.compile(
    r"(?:"
    r"\b(?:ML|EL)\d{2}XC[A-Z0-9-]*\b|"
    r"\bSL\d{2}XC[A-Z0-9-]*\b|"
    r"\b(?:13|14)ACX[A-Z0-9-]*\b|"
    r"\b(?:GLXS|GSX|ALXS|ASX)[A-Z0-9-]{4,}\b|"
    r"\bYCG[A-Z0-9-]{4,}\b|"
    r"\b24[A-Z]{2}[A-Z0-9-]{4,}\b|"
    r"\bRA1(?:3|4|6|7|8)[A-Z0-9-]{3,}\b|"
    r"\b4SCU[A-Z0-9-]{4,}\b"
    r")",
    re.I,
)

POSTAL_RE = re.compile(r"\b([A-Z]\d[A-Z])\s*(\d[A-Z]\d)\b", re.I)
UNIT_RE = re.compile(
    r"(?:\s+#\s*[A-Z0-9-]+|\s+\b(?:UNIT|APT|APARTMENT|SUITE)\s*[#-]?\s*[A-Z0-9-]+)\s*$",
    re.I,
)
TORONTO_CITY_NAMES = {
    "TORONTO",
    "NORTH YORK",
    "SCARBOROUGH",
    "ETOBICOKE",
    "EAST YORK",
    "YORK",
    "CENTRAL TORONTO",
}

STREET_SUFFIXES = {
    "AV": "AVE",
    "AVENUE": "AVE",
    "BLVD": "BLVD",
    "BOULEVARD": "BLVD",
    "CIR": "CIR",
    "CIRCLE": "CIR",
    "CRT": "CRT",
    "COURT": "CRT",
    "CRES": "CRES",
    "CRESCENT": "CRES",
    "DR": "DR",
    "DRIVE": "DR",
    "GDNS": "GDNS",
    "GARDENS": "GDNS",
    "GATE": "GATE",
    "GRV": "GRV",
    "GROVE": "GRV",
    "HTS": "HTS",
    "HEIGHTS": "HTS",
    "LANE": "LANE",
    "LINE": "LINE",
    "PL": "PL",
    "PLACE": "PL",
    "PKWY": "PKWY",
    "PARKWAY": "PKWY",
    "RD": "RD",
    "ROAD": "RD",
    "SQ": "SQ",
    "SQUARE": "SQ",
    "ST": "ST",
    "STREET": "ST",
    "TER": "TER",
    "TERRACE": "TER",
    "TRL": "TRL",
    "TRAIL": "TRL",
    "WAY": "WAY",
}
DIRECTION_TOKENS = {
    "N": "N",
    "NORTH": "N",
    "S": "S",
    "SOUTH": "S",
    "E": "E",
    "EAST": "E",
    "W": "W",
    "WEST": "W",
}


@dataclass
class InvoiceLocation:
    raw_address: str
    street_line: str
    city: str
    postal: str
    has_unit: bool
    exact_key: str
    relaxed_key: str
    equipment: set[str] = field(default_factory=set)
    evidence: set[str] = field(default_factory=set)
    models: set[str] = field(default_factory=set)


@dataclass
class PermitCandidate:
    source: str
    permit_num: str
    revision_num: str
    permit_type: str
    structure_type: str
    work: str
    postal: str
    status: str
    description: str
    current_use: str
    proposed_use: str
    residential_sqm: float | None
    match_method: str

    @property
    def residential_sqft(self) -> float | None:
        if self.residential_sqm is None:
            return None
        return self.residential_sqm * SQM_TO_SQFT

    @property
    def gfa_classification(self) -> str:
        if self.residential_sqm is None or self.residential_sqm <= 0:
            return "no_residential_gfa"
        text = " ".join(
            (self.permit_type, self.structure_type, self.work, self.description)
        ).upper()
        if "NEW BUILDING" in text or "NEW HOUSE" in text:
            return "possible_whole_building_new_construction"
        return "permit_scope_only_not_house_area"


def log(message: str) -> None:
    print(message, file=sys.stderr, flush=True)


def column_index(cell_reference: str) -> int:
    result = 0
    for character in cell_reference:
        if not character.isalpha():
            break
        result = result * 26 + ord(character.upper()) - 64
    return result - 1


def load_shared_strings(archive: zipfile.ZipFile) -> list[str]:
    try:
        root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
    except KeyError:
        return []
    return [
        "".join(text.text or "" for text in item.iter(XLSX_NS + "t"))
        for item in root.findall(XLSX_NS + "si")
    ]


def iter_xlsx_rows(path: Path) -> Iterator[dict[str, str]]:
    """Stream the first XLSX worksheet as dictionaries."""
    with zipfile.ZipFile(path) as archive:
        shared_strings = load_shared_strings(archive)
        header: list[str] | None = None
        with archive.open("xl/worksheets/sheet1.xml") as worksheet:
            for _, row in ET.iterparse(worksheet, events=("end",)):
                if row.tag != XLSX_NS + "row":
                    continue
                values: dict[int, str] = {}
                for cell in row.findall(XLSX_NS + "c"):
                    index = column_index(cell.attrib.get("r", ""))
                    value_node = cell.find(XLSX_NS + "v")
                    value = "" if value_node is None else (value_node.text or "")
                    cell_type = cell.attrib.get("t")
                    if cell_type == "s" and value:
                        value = shared_strings[int(value)]
                    elif cell_type == "inlineStr":
                        value = "".join(
                            node.text or "" for node in cell.iter(XLSX_NS + "t")
                        )
                    values[index] = value.strip()

                if header is None:
                    max_index = max(values, default=-1)
                    header = [values.get(i, "") for i in range(max_index + 1)]
                else:
                    yield {
                        name: values.get(index, "")
                        for index, name in enumerate(header)
                        if name
                    }
                row.clear()


def ascii_upper(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    return "".join(c for c in normalized if not unicodedata.combining(c)).upper()


def normalize_number(value: str) -> str:
    return re.sub(r"[^A-Z0-9-]", "", ascii_upper(value))


def normalize_street_tokens(value: str, *, relaxed: bool) -> str:
    value = ascii_upper(value).replace("&", " AND ")
    value = re.sub(r"[^A-Z0-9]+", " ", value)
    tokens = [token for token in value.split() if token]
    normalized: list[str] = []
    for token in tokens:
        if token == "SAINT":
            token = "ST"
        token = STREET_SUFFIXES.get(token, DIRECTION_TOKENS.get(token, token))
        normalized.append(token)
    if relaxed:
        normalized = [
            token
            for token in normalized
            if token not in set(STREET_SUFFIXES.values())
            and token not in set(DIRECTION_TOKENS.values())
        ]
    return " ".join(normalized)


def parse_invoice_address(raw_address: str) -> tuple[str, str, str, bool, str, str]:
    parts = [part.strip() for part in raw_address.split(",")]
    street_line = parts[0] if parts else raw_address.strip()
    has_unit = bool(UNIT_RE.search(street_line) or re.search(r"\s+#", street_line))
    street_without_unit = UNIT_RE.sub("", street_line).strip()

    city = ""
    if len(parts) >= 2:
        city = ascii_upper(parts[1]).strip()

    postal_match = POSTAL_RE.search(raw_address)
    postal = ""
    if postal_match:
        postal = (postal_match.group(1) + postal_match.group(2)).upper()

    number_match = re.match(r"^\s*([0-9]+(?:-[0-9]+)?[A-Z]?)\s+(.+)$", street_without_unit, re.I)
    if not number_match:
        return street_line, city, postal, has_unit, "", ""
    street_number = normalize_number(number_match.group(1))
    street_name = number_match.group(2)
    exact_key = f"{street_number}|{normalize_street_tokens(street_name, relaxed=False)}"
    relaxed_key = f"{street_number}|{normalize_street_tokens(street_name, relaxed=True)}"
    return street_line, city, postal, has_unit, exact_key, relaxed_key


def permit_address_keys(row: dict[str, str]) -> tuple[str, str]:
    number = normalize_number(row.get("STREET_NUM", ""))
    street = " ".join(
        part
        for part in (
            row.get("STREET_NAME", ""),
            row.get("STREET_TYPE", ""),
            row.get("STREET_DIRECTION", ""),
        )
        if part
    )
    if not number or not street:
        return "", ""
    return (
        f"{number}|{normalize_street_tokens(street, relaxed=False)}",
        f"{number}|{normalize_street_tokens(street, relaxed=True)}",
    )


def equipment_hits(row: dict[str, str]) -> tuple[set[str], set[str]]:
    name = row.get("Item Name", "")
    code = row.get("Item Code", "")
    model = row.get("Model on Invoice", "")
    text = " ".join((name, code, model))
    equipment: set[str] = set()
    evidence: set[str] = set()

    if FURNACE_MARKER_RE.search(text):
        equipment.add("furnace")
        evidence.add("furnace_install_marker")
    if AC_MARKER_RE.search(text):
        equipment.add("air_conditioner")
        evidence.add("ac_install_marker")
    if FURNACE_MODEL_RE.search(text):
        equipment.add("furnace")
        evidence.add("recognized_furnace_model")
    if AC_MODEL_RE.search(text):
        equipment.add("air_conditioner")
        evidence.add("recognized_ac_model")
    return equipment, evidence


def load_invoice_locations(path: Path) -> tuple[dict[str, InvoiceLocation], dict[str, int]]:
    locations: dict[str, InvoiceLocation] = {}
    stats = {"rows": 0, "rows_with_address": 0, "raw_locations": 0}
    for row in iter_xlsx_rows(path):
        stats["rows"] += 1
        raw_address = row.get("Location Address", "").strip()
        if not raw_address:
            continue
        stats["rows_with_address"] += 1
        if raw_address not in locations:
            street, city, postal, has_unit, exact_key, relaxed_key = parse_invoice_address(
                raw_address
            )
            locations[raw_address] = InvoiceLocation(
                raw_address=raw_address,
                street_line=street,
                city=city,
                postal=postal,
                has_unit=has_unit,
                exact_key=exact_key,
                relaxed_key=relaxed_key,
            )
        location = locations[raw_address]
        equipment, evidence = equipment_hits(row)
        location.equipment.update(equipment)
        location.evidence.update(evidence)
        model = row.get("Model on Invoice", "").strip()
        if model and equipment:
            location.models.add(model)
    stats["raw_locations"] = len(locations)
    return locations, stats


def is_toronto_location(location: InvoiceLocation) -> bool:
    return location.postal.startswith("M") or location.city in TORONTO_CITY_NAMES


def download_if_needed(url: str, destination: Path, refresh: bool) -> None:
    if destination.exists() and destination.stat().st_size > 0 and not refresh:
        log(f"Using cached {destination.name} ({destination.stat().st_size / 1_000_000:.1f} MB)")
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".part")
    log(f"Downloading {destination.name} ...")
    request = urllib.request.Request(url, headers={"User-Agent": "hvac-open-data-audit/1.0"})
    with urllib.request.urlopen(request, timeout=120) as response, temporary.open("wb") as output:
        total = int(response.headers.get("Content-Length", "0") or 0)
        downloaded = 0
        next_report = 25_000_000
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            output.write(chunk)
            downloaded += len(chunk)
            if downloaded >= next_report:
                if total:
                    log(f"  {downloaded / 1_000_000:.0f}/{total / 1_000_000:.0f} MB")
                else:
                    log(f"  {downloaded / 1_000_000:.0f} MB")
                next_report += 25_000_000
    temporary.replace(destination)


def parse_float(value: str) -> float | None:
    value = (value or "").strip().replace(",", "")
    if not value:
        return None
    try:
        result = float(value)
    except ValueError:
        return None
    return result if result > 0 else None


def index_targets(
    targets: dict[str, InvoiceLocation],
) -> tuple[dict[str, set[str]], dict[str, set[str]]]:
    exact: dict[str, set[str]] = defaultdict(set)
    relaxed: dict[str, set[str]] = defaultdict(set)
    for address, location in targets.items():
        if location.exact_key:
            exact[location.exact_key].add(address)
        if location.relaxed_key:
            relaxed[location.relaxed_key].add(address)
    return exact, relaxed


def scan_permits(
    source: str,
    csv_path: Path,
    exact_targets: dict[str, set[str]],
    relaxed_targets: dict[str, set[str]],
    target_locations: dict[str, InvoiceLocation],
    matches: dict[str, list[PermitCandidate]],
) -> tuple[int, int]:
    rows = 0
    matched_rows = 0
    with csv_path.open("r", encoding="utf-8-sig", newline="") as source_file:
        reader = csv.DictReader(source_file)
        for row in reader:
            rows += 1
            exact_key, relaxed_key = permit_address_keys(row)
            target_addresses: set[str] = set()
            match_method = ""
            if exact_key and exact_key in exact_targets:
                target_addresses.update(exact_targets[exact_key])
                match_method = "exact_normalized_address"
            elif relaxed_key and relaxed_key in relaxed_targets:
                target_addresses.update(relaxed_targets[relaxed_key])
                match_method = "relaxed_address_without_suffix_direction"
            permit_postal = re.sub(r"\s+", "", row.get("POSTAL", "").upper())
            permit_fsa = permit_postal[:3]
            if permit_fsa:
                target_addresses = {
                    address
                    for address in target_addresses
                    if not target_locations[address].postal
                    or target_locations[address].postal[:3] == permit_fsa
                }
            if not target_addresses:
                continue
            matched_rows += 1
            candidate = PermitCandidate(
                source=source,
                permit_num=row.get("PERMIT_NUM", ""),
                revision_num=row.get("REVISION_NUM", ""),
                permit_type=row.get("PERMIT_TYPE", ""),
                structure_type=row.get("STRUCTURE_TYPE", ""),
                work=row.get("WORK", ""),
                postal=permit_postal,
                status=row.get("STATUS", ""),
                description=row.get("DESCRIPTION", ""),
                current_use=row.get("CURRENT_USE", ""),
                proposed_use=row.get("PROPOSED_USE", ""),
                residential_sqm=parse_float(row.get("RESIDENTIAL", "")),
                match_method=match_method,
            )
            for address in target_addresses:
                matches[address].append(candidate)
    return rows, matched_rows


def candidate_sort_key(candidate: PermitCandidate) -> tuple[int, float]:
    classification_rank = {
        "possible_whole_building_new_construction": 2,
        "permit_scope_only_not_house_area": 1,
        "no_residential_gfa": 0,
    }[candidate.gfa_classification]
    return classification_rank, candidate.residential_sqm or 0.0


def is_plausible_single_home_gfa(
    location: InvoiceLocation, candidate: PermitCandidate
) -> bool:
    """Conservative flag for a possible whole-home training label."""
    if location.has_unit:
        return False
    if candidate.gfa_classification != "possible_whole_building_new_construction":
        return False
    square_feet = candidate.residential_sqft
    if square_feet is None or not 500 <= square_feet <= 6_000:
        return False
    structure = candidate.structure_type.upper()
    return any(
        value in structure
        for value in ("SFD - DETACHED", "SFD - SEMI-DETACHED", "2 UNIT - DETACHED")
    )


def write_outputs(
    output_dir: Path,
    eligible: dict[str, InvoiceLocation],
    toronto_targets: dict[str, InvoiceLocation],
    matches: dict[str, list[PermitCandidate]],
    summary: dict[str, object],
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    location_path = output_dir / "toronto_permit_address_matches.csv"
    with location_path.open("w", encoding="utf-8", newline="") as output:
        fields = [
            "invoice_address",
            "postal_code",
            "equipment",
            "equipment_filter_evidence",
            "recognized_equipment_models",
            "contains_unit_number",
            "in_toronto_scope",
            "matched_any_permit",
            "permit_record_count",
            "matched_residential_gfa",
            "possible_whole_building_gfa",
            "plausible_single_home_gfa",
            "best_candidate_sqft",
            "best_candidate_classification",
            "best_candidate_permit",
            "best_candidate_work",
            "best_candidate_structure_type",
            "best_candidate_match_method",
        ]
        writer = csv.DictWriter(output, fieldnames=fields)
        writer.writeheader()
        for address, location in sorted(eligible.items()):
            candidates = matches.get(address, [])
            gfa_candidates = [candidate for candidate in candidates if candidate.residential_sqm]
            whole_candidates = [
                candidate
                for candidate in candidates
                if candidate.gfa_classification
                == "possible_whole_building_new_construction"
            ]
            single_home_candidates = [
                candidate
                for candidate in candidates
                if is_plausible_single_home_gfa(location, candidate)
            ]
            best = max(candidates, key=candidate_sort_key) if candidates else None
            writer.writerow(
                {
                    "invoice_address": address,
                    "postal_code": location.postal,
                    "equipment": ";".join(sorted(location.equipment)),
                    "equipment_filter_evidence": ";".join(sorted(location.evidence)),
                    "recognized_equipment_models": ";".join(sorted(location.models)),
                    "contains_unit_number": str(location.has_unit).lower(),
                    "in_toronto_scope": str(address in toronto_targets).lower(),
                    "matched_any_permit": str(bool(candidates)).lower(),
                    "permit_record_count": len(candidates),
                    "matched_residential_gfa": str(bool(gfa_candidates)).lower(),
                    "possible_whole_building_gfa": str(bool(whole_candidates)).lower(),
                    "plausible_single_home_gfa": str(bool(single_home_candidates)).lower(),
                    "best_candidate_sqft": (
                        f"{best.residential_sqft:.1f}"
                        if best and best.residential_sqft is not None
                        else ""
                    ),
                    "best_candidate_classification": (
                        best.gfa_classification if best else ""
                    ),
                    "best_candidate_permit": best.permit_num if best else "",
                    "best_candidate_work": best.work if best else "",
                    "best_candidate_structure_type": best.structure_type if best else "",
                    "best_candidate_match_method": best.match_method if best else "",
                }
            )

    candidates_path = output_dir / "toronto_permit_gfa_candidates.csv"
    with candidates_path.open("w", encoding="utf-8", newline="") as output:
        fields = [
            "invoice_address",
            "equipment",
            "source_dataset",
            "permit_num",
            "revision_num",
            "permit_type",
            "structure_type",
            "work",
            "status",
            "permit_postal_fsa",
            "current_use",
            "proposed_use",
            "residential_gfa_sqm",
            "residential_gfa_sqft",
            "gfa_classification",
            "plausible_single_home_gfa",
            "match_method",
            "description",
        ]
        writer = csv.DictWriter(output, fieldnames=fields)
        writer.writeheader()
        for address in sorted(toronto_targets):
            location = toronto_targets[address]
            for candidate in matches.get(address, []):
                if candidate.residential_sqm is None:
                    continue
                writer.writerow(
                    {
                        "invoice_address": address,
                        "equipment": ";".join(sorted(location.equipment)),
                        "source_dataset": candidate.source,
                        "permit_num": candidate.permit_num,
                        "revision_num": candidate.revision_num,
                        "permit_type": candidate.permit_type,
                        "structure_type": candidate.structure_type,
                        "work": candidate.work,
                        "status": candidate.status,
                        "permit_postal_fsa": candidate.postal,
                        "current_use": candidate.current_use,
                        "proposed_use": candidate.proposed_use,
                        "residential_gfa_sqm": f"{candidate.residential_sqm:.2f}",
                        "residential_gfa_sqft": f"{candidate.residential_sqft:.1f}",
                        "gfa_classification": candidate.gfa_classification,
                        "plausible_single_home_gfa": str(
                            is_plausible_single_home_gfa(location, candidate)
                        ).lower(),
                        "match_method": candidate.match_method,
                        "description": candidate.description,
                    }
                )

    training_path = output_dir / "plausible_single_home_training_candidates.csv"
    with training_path.open("w", encoding="utf-8", newline="") as output:
        fields = [
            "invoice_address",
            "postal_code",
            "equipment",
            "recognized_equipment_models",
            "residential_gfa_sqft",
            "permit_num",
            "permit_source",
            "structure_type",
            "work",
            "match_method",
            "distinct_plausible_gfa_values",
            "needs_manual_review",
        ]
        writer = csv.DictWriter(output, fieldnames=fields)
        writer.writeheader()
        for address, location in sorted(toronto_targets.items()):
            candidates = [
                candidate
                for candidate in matches.get(address, [])
                if is_plausible_single_home_gfa(location, candidate)
            ]
            if not candidates:
                continue
            best = max(candidates, key=candidate_sort_key)
            distinct_values = sorted(
                {round(candidate.residential_sqft or 0, 1) for candidate in candidates}
            )
            writer.writerow(
                {
                    "invoice_address": address,
                    "postal_code": location.postal,
                    "equipment": ";".join(sorted(location.equipment)),
                    "recognized_equipment_models": ";".join(sorted(location.models)),
                    "residential_gfa_sqft": f"{best.residential_sqft:.1f}",
                    "permit_num": best.permit_num,
                    "permit_source": best.source,
                    "structure_type": best.structure_type,
                    "work": best.work,
                    "match_method": best.match_method,
                    "distinct_plausible_gfa_values": ";".join(
                        f"{value:.1f}" for value in distinct_values
                    ),
                    "needs_manual_review": str(len(distinct_values) > 1).lower(),
                }
            )

    summary_path = output_dir / "toronto_permit_match_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    log(f"Wrote {location_path}")
    log(f"Wrote {candidates_path}")
    log(f"Wrote {training_path}")
    log(f"Wrote {summary_path}")


def build_summary(
    workbook_stats: dict[str, int],
    eligible: dict[str, InvoiceLocation],
    toronto_targets: dict[str, InvoiceLocation],
    matches: dict[str, list[PermitCandidate]],
    dataset_stats: dict[str, dict[str, int]],
    elapsed_seconds: float,
) -> dict[str, object]:
    matched = {address for address in toronto_targets if matches.get(address)}
    with_gfa = {
        address
        for address in toronto_targets
        if any(candidate.residential_sqm for candidate in matches.get(address, []))
    }
    with_possible_whole = {
        address
        for address in toronto_targets
        if any(
            candidate.gfa_classification
            == "possible_whole_building_new_construction"
            for candidate in matches.get(address, [])
        )
    }
    with_plausible_single_home = {
        address
        for address, location in toronto_targets.items()
        if any(
            is_plausible_single_home_gfa(location, candidate)
            for candidate in matches.get(address, [])
        )
    }
    conflicting_plausible_gfa = {
        address
        for address in with_plausible_single_home
        if len(
            {
                round(candidate.residential_sqft or 0, 1)
                for candidate in matches.get(address, [])
                if is_plausible_single_home_gfa(
                    toronto_targets[address], candidate
                )
            }
        )
        > 1
    }
    marker_only = {
        address
        for address, location in eligible.items()
        if any("install_marker" in evidence for evidence in location.evidence)
    }
    model_only = set(eligible) - marker_only
    return {
        "workbook": workbook_stats,
        "equipment_filter": {
            "eligible_unique_locations": len(eligible),
            "eligible_unique_normalized_properties": len(
                {
                    (location.exact_key, location.postal)
                    for location in eligible.values()
                    if location.exact_key
                }
            ),
            "furnace_locations": sum(
                "furnace" in location.equipment for location in eligible.values()
            ),
            "air_conditioner_locations": sum(
                "air_conditioner" in location.equipment for location in eligible.values()
            ),
            "locations_with_both": sum(
                location.equipment == {"furnace", "air_conditioner"}
                for location in eligible.values()
            ),
            "locations_supported_by_install_marker": len(marker_only),
            "locations_supported_only_by_model_pattern": len(model_only),
        },
        "toronto_scope": {
            "eligible_locations": len(toronto_targets),
            "eligible_unique_normalized_properties": len(
                {
                    (location.exact_key, location.postal)
                    for location in toronto_targets.values()
                    if location.exact_key
                }
            ),
            "locations_with_unit_numbers": sum(
                location.has_unit for location in toronto_targets.values()
            ),
            "locations_with_parseable_street_addresses": sum(
                bool(location.exact_key) for location in toronto_targets.values()
            ),
        },
        "permit_coverage": {
            "matched_any_permit": len(matched),
            "matched_any_permit_percent": round(
                100 * len(matched) / len(toronto_targets), 2
            )
            if toronto_targets
            else 0,
            "matched_residential_gfa": len(with_gfa),
            "matched_residential_gfa_percent": round(
                100 * len(with_gfa) / len(toronto_targets), 2
            )
            if toronto_targets
            else 0,
            "possible_whole_building_new_construction_gfa": len(with_possible_whole),
            "possible_whole_building_new_construction_gfa_percent": round(
                100 * len(with_possible_whole) / len(toronto_targets), 2
            )
            if toronto_targets
            else 0,
            "plausible_single_home_new_construction_gfa": len(
                with_plausible_single_home
            ),
            "plausible_single_home_new_construction_gfa_percent": round(
                100 * len(with_plausible_single_home) / len(toronto_targets), 2
            )
            if toronto_targets
            else 0,
            "plausible_single_home_conflicting_gfa_values": len(
                conflicting_plausible_gfa
            ),
        },
        "open_data_rows": dataset_stats,
        "elapsed_seconds": round(elapsed_seconds, 2),
        "warnings": [
            "Toronto permit RESIDENTIAL GFA describes the permitted work and is not necessarily total house area.",
            "Only new-building/new-house GFA rows are flagged as possible whole-building values; they still require validation.",
            "Toronto open data cannot cover invoice locations in other Ontario municipalities.",
            "The equipment classifier is conservative and may miss uncommon model families without an installation marker.",
        ],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workbook", type=Path, help="Invoice Items Report XLSX file")
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=Path(".cache/toronto_open_data"),
        help="download cache for Toronto CSV files",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("output/toronto_permit_match"),
        help="directory for summary and match CSV files",
    )
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="redownload Toronto datasets even when cached",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    started = time.monotonic()
    if not args.workbook.is_file():
        print(f"Workbook not found: {args.workbook}", file=sys.stderr)
        return 2

    log(f"Reading invoice workbook: {args.workbook}")
    locations, workbook_stats = load_invoice_locations(args.workbook)
    eligible = {
        address: location
        for address, location in locations.items()
        if location.equipment
    }
    toronto_targets = {
        address: location
        for address, location in eligible.items()
        if is_toronto_location(location)
    }
    log(
        f"Found {len(eligible):,} furnace/A/C locations; "
        f"{len(toronto_targets):,} are in Toronto scope"
    )

    exact_targets, relaxed_targets = index_targets(toronto_targets)
    matches: dict[str, list[PermitCandidate]] = defaultdict(list)
    dataset_stats: dict[str, dict[str, int]] = {}

    for source, url in TORONTO_DATASETS:
        csv_path = args.cache_dir / f"{source}.csv"
        download_if_needed(url, csv_path, args.refresh)
        log(f"Scanning {source} ...")
        rows, matched_rows = scan_permits(
            source,
            csv_path,
            exact_targets,
            relaxed_targets,
            toronto_targets,
            matches,
        )
        dataset_stats[source] = {"rows_scanned": rows, "matched_rows": matched_rows}
        log(f"  scanned {rows:,} rows; {matched_rows:,} permit rows matched")

    summary = build_summary(
        workbook_stats,
        eligible,
        toronto_targets,
        matches,
        dataset_stats,
        time.monotonic() - started,
    )
    write_outputs(
        args.output_dir, eligible, toronto_targets, matches, summary
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
