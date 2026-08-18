#!/usr/bin/env python3
"""Cent-accurate full reconciliation of source calculations and distributions."""
from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

CENT = Decimal("0.01")


def money(value: str | Decimal) -> Decimal:
    return Decimal(value).quantize(CENT, rounding=ROUND_HALF_UP)


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def reconcile(source_rows: list[dict[str, str]], output_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    source_by_id: dict[str, list[dict[str, str]]] = defaultdict(list)
    output_by_id: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in source_rows:
        source_by_id[row["client_id"]].append(row)
    for row in output_rows:
        output_by_id[row["client_id"]].append(row)

    findings: list[dict[str, str]] = []
    for client_id in sorted(set(source_by_id) | set(output_by_id)):
        sources, outputs = source_by_id.get(client_id, []), output_by_id.get(client_id, [])
        source, output = (sources[0] if sources else None), (outputs[0] if outputs else None)
        expected = money(source["expected_net_amount"]) if source else None
        distributed = money(output["distributed_amount"]) if output else None
        variance = distributed - expected if expected is not None and distributed is not None else None

        if len(outputs) > 1:
            kind = "Duplicate distribution record"
            detail = f"{len(outputs)} output rows found; expected exactly 1"
        elif len(sources) > 1:
            kind = "Duplicate source record"
            detail = f"{len(sources)} source rows found; expected exactly 1"
        elif source and not output:
            kind = "Missing distribution record"
            detail = "Source calculation exists but distribution output is missing"
        elif output and not source:
            kind = "Unexpected / orphan output"
            detail = "Distribution output exists with no source calculation"
        else:
            recalculated = money(Decimal(source["source_amount"]) * (Decimal("1") - Decimal(source["fee_pct"]) / Decimal("100")))
            if recalculated != expected:
                kind = "Source calculation error"
                detail = f"Provided expected {expected} differs from recalculated {recalculated}"
            elif variance != Decimal("0.00"):
                kind = "Rounding / amount mismatch" if abs(variance) <= CENT else "Calculation / business-rule error"
                detail = f"Distributed {distributed} differs from expected {expected} by {variance}"
            elif source["client_name"] != output["client_name"]:
                kind = "Metadata mismatch"
                detail = f"Client name differs: {source['client_name']} vs {output['client_name']}"
            else:
                continue

        findings.append({
            "discrepancy_type": kind,
            "client_id": client_id,
            "client_name": (source or output)["client_name"],
            "expected_amount": f"{expected:.2f}" if expected is not None else "",
            "distributed_amount": f"{distributed:.2f}" if distributed is not None else "",
            "variance": f"{variance:.2f}" if variance is not None else "",
            "source_record_count": str(len(sources)),
            "output_record_count": str(len(outputs)),
            "details": detail,
        })
    return findings


def write_reports(findings: list[dict[str, str]], report_dir: Path) -> None:
    report_dir.mkdir(parents=True, exist_ok=True)
    fields = ["discrepancy_type", "client_id", "client_name", "expected_amount", "distributed_amount", "variance", "source_record_count", "output_record_count", "details"]
    with (report_dir / "discrepancy_details.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader(); writer.writerows(findings)

    counts = Counter(item["discrepancy_type"] for item in findings)
    with (report_dir / "discrepancy_summary.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["discrepancy_type", "count", "affected_clients"])
        for kind in sorted(counts):
            clients = ", ".join(item["client_id"] for item in findings if item["discrepancy_type"] == kind)
            writer.writerow([kind, counts[kind], clients])
        writer.writerow(["TOTAL", len(findings), ", ".join(item["client_id"] for item in findings)])
    (report_dir / "discrepancies.json").write_text(json.dumps(findings, indent=2), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=Path("data/source_calculations.csv"))
    parser.add_argument("--output", type=Path, default=Path("data/distribution_output.csv"))
    parser.add_argument("--report-dir", type=Path, default=Path("reports/generated"))
    args = parser.parse_args()
    findings = reconcile(load_csv(args.source), load_csv(args.output))
    write_reports(findings, args.report_dir)
    print(json.dumps({"discrepancy_count": len(findings), "affected_clients": [f["client_id"] for f in findings]}, indent=2))
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
