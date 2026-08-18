#!/usr/bin/env python3
"""Execute semicolon-separated investigation queries and export their results."""
import argparse, csv, sqlite3
from pathlib import Path


def statements(text: str):
    cleaned = "\n".join(line for line in text.splitlines() if not line.lstrip().startswith("--"))
    return [part.strip() for part in cleaned.split(";") if part.strip()]


def main():
    parser = argparse.ArgumentParser(); parser.add_argument("--database", type=Path, default=Path("data/distribution_qa.db")); parser.add_argument("--queries", type=Path, default=Path("sql/investigation_queries.sql")); parser.add_argument("--report-dir", type=Path, default=Path("reports/generated/sql")); args = parser.parse_args()
    args.report_dir.mkdir(parents=True, exist_ok=True)
    names = ["missing_approved_transactions", "monthly_distributed_totals", "amount_variances_over_one_cent"]
    with sqlite3.connect(args.database) as db:
        db.row_factory = sqlite3.Row
        for name, query in zip(names, statements(args.queries.read_text(encoding="utf-8"))):
            rows = db.execute(query).fetchall(); path = args.report_dir / f"{name}.csv"
            with path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.writer(handle)
                if rows: writer.writerow(rows[0].keys()); writer.writerows([tuple(row) for row in rows])
            print(f"{name}: {len(rows)} row(s)")


if __name__ == "__main__": main()
