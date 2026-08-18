# Bulk Financial Distribution Validation & QA

Take-home solution covering cent-accurate bulk validation, SQLite investigation/root-cause analysis, and locally mocked regression automation.

## What is included

- `src/validate_distributions.py` — reconciles source and output CSVs with `Decimal` arithmetic and categorises anomalies.
- `sql/investigation_queries.sql` — the three requested investigation queries.
- `src/seed_database.py` — creates the simulated three-month SQLite fixture.
- `src/run_sql_investigation.py` — runs the SQL investigation and writes reviewable CSV results.
- `src/status_service.py` — deterministic, mocked distribution status-check service.
- `tests/` — unit/regression tests for validation and status-check scenarios.
- `reports/discrepancy_summary.xlsx` — pivot-equivalent summary and affected records.
- `SOLUTION.md` — design, findings, scaling approach, bug report, regression strategy, trade-offs, and AI-use note.

## Requirements

- Python 3.10 or newer
- No third-party Python packages
- No API, network, or external database connection

## Quick start

From the repository root:

```bash
python3 src/seed_database.py
python3 src/validate_distributions.py
python3 src/run_sql_investigation.py
python3 -m unittest discover -s tests -v
```

Generated output is written to `reports/generated/`. The supplied input files are read only and are never modified.
The Task 1 validator intentionally returns exit code `1` when discrepancies exist, making it suitable for a CI quality gate; its reports are still generated normally.

## Run individual parts

Task 1 validation:

```bash
python3 src/validate_distributions.py \
  --source data/source_calculations.csv \
  --output data/distribution_output.csv \
  --report-dir reports/generated
```

Task 2 SQL investigation:

```bash
python3 src/seed_database.py --database data/distribution_qa.db
python3 src/run_sql_investigation.py \
  --database data/distribution_qa.db \
  --queries sql/investigation_queries.sql \
  --report-dir reports/generated/sql
```

Task 3 mocked status check:

```bash
python3 src/status_service.py C001 2026-06
python3 -m unittest tests.test_status_service -v
```

Example response:

```json
{"client_id": "C001", "period": "2026-06", "status": "COMPLETED", "distributed_amount": "9800.00"}
```

## Review order

1. Read `SOLUTION.md`.
2. Open `reports/discrepancy_summary.xlsx`.
3. Review `sql/investigation_queries.sql` and `reports/generated/sql/`.
4. Run the tests and inspect `tests/test_status_service.py`.

## Assumption about supplied files

The original binary/database attachments were not available while this repository was assembled. The `data/` fixtures reproduce the sample data in the brief, and `seed_database.py` creates a deterministic simulated three-month database matching the stated schema. If the original files are supplied, place them under the same filenames; the validator and SQL runner read them without altering their contents.
