# Solution: Bulk Financial Distribution Validation & QA

## Executive summary

The solution uses exact decimal arithmetic, explicit reconciliation rules, SQL anti-joins/aggregations, and deterministic mocked regression tests. The Task 1 sample contains **5 discrepancy categories affecting 5 clients**: C002, C005, C007, C011, and C013.

## Task 1 — Bulk distribution validation

### Design

`src/validate_distributions.py` reads both CSVs without modifying them and:

1. Parses monetary values with Python `Decimal`, never binary floating-point.
2. Recalculates net amount as `source_amount × (1 − fee_pct)`, rounded to cents using `ROUND_HALF_UP`.
3. Checks whether the provided expected net agrees with the recalculation.
4. Groups each file by client ID to detect duplicates before doing the one-to-one comparison.
5. Performs a full outer-style reconciliation so missing and unexpected clients remain visible.
6. Classifies each affected client once using a deterministic precedence: duplicate, missing output, unexpected output, source calculation error, amount mismatch, metadata mismatch.
7. Writes detailed and summary CSV outputs suitable for audit and creates the supplied pivot-equivalent Excel workbook.

### Findings

| Type | Count | Affected client(s) | Evidence |
| --- | ---: | --- | --- |
| Rounding / amount mismatch | 1 | C002 | Expected 5,145.74; distributed 5,145.73; variance -0.01 |
| Missing distribution record | 1 | C005 | Source expected 2,940.00; no output row |
| Duplicate distribution record | 1 | C007 | Two identical output records for 44,100.00 |
| Calculation / business-rule error | 1 | C011 | Negative expected net -196.00 was output as 0.00 |
| Unexpected / orphan output | 1 | C013 | Output 320.00 has no source calculation |
| **Total** | **5** | **5 clients** | See `reports/discrepancy_summary.xlsx` |

The one-cent C002 variance is labelled a rounding/amount mismatch because the output does not equal the supplied cent-rounded expected net. C011 is materially different and likely reflects unsupported negative-amount handling or a silent floor-to-zero rule.

### Scaling to thousands of clients

For a production-sized run I would stage source and output data in database tables keyed by `(period, client_id)`, enforce uniqueness where the business rules require it, and run set-based reconciliation queries. Amounts would use fixed precision (`DECIMAL`, or integer minor units/cents), never floating-point. The job would partition by period/batch, write exceptions to an immutable audit table, and expose control totals: record counts, gross amount, fees, expected net, distributed total, and variance.

At higher volume, only discrepancies and aggregate controls need to leave the database. The same classification rules can execute in SQL or a distributed job, while the small exception result feeds Excel/BI. Automation would add schema/contract checks, idempotency checks, retry/re-run checks, and thresholds that fail the release or payment gate when counts or financial totals do not reconcile.

## Task 2 — SQL investigation and root cause analysis

### Query approach

The requested SQL is in `sql/investigation_queries.sql`:

- A `NOT EXISTS` anti-join finds distributions without an approved transaction tied to the same `distribution_id`.
- `substr(period, 1, 7)` groups distributed totals by month.
- A CTE calculates expected net to cents and compares it with the distribution using `ABS(variance) > 0.01` (with a tiny numeric guard for SQLite floating storage).

The seeded fixture produces reviewable results under `reports/generated/sql/`. On the included dataset:

- Distributions without an approved transaction: `D012 / C004 / 2026-03` and `D013 / C005 / 2026-03`.
- Monthly totals: Jan 2026 = 16,587.24; Feb 2026 = 16,587.26; Mar 2026 = 19,566.44.
- Amount variance greater than one cent: `C002 / 2026-02`, expected 5,145.74 vs distributed 5,145.76, variance 0.02.

### Bug report

**Title:** Batch distribution skips client when `fee_pct` is NULL due to divide-by-zero in `FeeCalculator.applyFee`

**Severity/Priority:** High / P1 for the affected batch; payment completeness is compromised.

**Environment/context:** Simulated batch job, period `2026-06`, run started `2026-06-14 02:14:07`, 4,812 clients loaded.

**Preconditions:** A processable client calculation exists for the batch period with `fee_pct = NULL` (example client C0453).

**Steps to reproduce:**

1. Create or select an eligible client calculation for period 2026-06.
2. Leave `fee_pct` NULL.
3. Run `BatchDistributionJob` for 2026-06.
4. Inspect the client output and batch log.

**Actual result:** C0453 is skipped. The job logs `ArithmeticException: / by zero` at `FeeCalculator.applyFee(FeeCalculator.java:87)`, through `DistributionProcessor.process(...:142)` and `BatchDistributionJob.run(...:64)`. A warning immediately identifies `fee_pct=NULL`. The batch continues and finishes with 4,811 successes and 1 failure.

**Expected result:** Invalid or missing fee configuration is rejected during pre-validation with a controlled, actionable validation error before payment calculation. If business rules define a default fee, that default must be applied explicitly and audited. No low-level arithmetic exception should occur, and the failed client must be visible in an exception/retry queue.

**Evidence and likely root cause:**

- Log start/loading: lines 1–3.
- Failed client C0453: lines 4–5.
- Stack trace points to fee calculation: lines 6–9.
- `fee_pct=NULL` warning: lines 10–11.
- Batch completion confirms one skipped record: lines 12–14.

The strongest inference is missing input validation/default handling for NULL `fee_pct`. The `/ by zero` error also suggests the implementation may transform the fee into a divisor or substitute zero before division. A source review at line 87 is required to confirm the exact expression.

**Business impact:** One client receives no distribution while the overall batch reports completion. This creates underpayment, reconciliation breaks, manual remediation, complaints, and financial/reputational risk. At scale, multiple NULL fee records could silently produce a partial batch.

**Recommended fix and tests:** Validate `fee_pct` before calculation; reject NULL/out-of-range values with a domain-specific error; define whether zero is valid; surface failed records operationally; add unit tests for NULL, zero, negative, and >100% fees plus an integration test proving the batch count and totals reconcile.

## Task 3 — automated regression coverage

### Implementation

`src/status_service.py` models the status-check contract behind a repository interface. `InMemoryDistributionRepository` is a deterministic mock, so tests make no external calls. The five tests cover:

1. Completed distribution returns exact amount.
2. Pending distribution returns status and 0.00.
3. Failed distribution returns status and 0.00.
4. Unknown client returns a not-found error.
5. Missing/invalid period returns a validation error.

This is service/API-layer automation rather than browser UI automation because the requirement is a data-returning status flow. It is faster, less brittle, and suitable for a release gate. A thin Playwright UI layer would be added only if an actual web interface existed.

### Two-day regression strategy

With a limited release window, I would prioritize by financial impact and detectability:

**Automated release gate:** calculation/rounding boundaries; positive, zero, and negative values; missing/duplicate/orphan records; fee boundaries including NULL; status contract; transaction approval linkage; batch totals/counts; idempotent re-run; failed-record isolation; and the five mocked status scenarios included here.

**Targeted manual/exploratory:** one end-to-end representative batch through calculation, approval, payment trigger, status display, exception handling, and reconciliation; role/approval controls; operational alerts; and review of a failed client’s retry path. Production-like control totals and logs should be captured as evidence.

**Deferred in this window:** exhaustive browser/device combinations, cosmetic UI checks, broad performance soak, every region/client permutation, and non-critical reporting exports. The trade-off is reduced confidence in presentation, rare combinations, and sustained-load behaviour. I accept that risk temporarily because cent accuracy, payment completeness, approval linkage, failure recovery, and auditability present the highest immediate loss exposure. Deferred items should be scheduled immediately after release or block release if recent changes touched those areas.

The automation built here reflects that prioritisation: it is deterministic, quick, data-focused, negative-case aware, and can run on every commit without infrastructure.


## Limitations and assumptions

- The original attached SQLite/database and log files were not available during assembly, so deterministic simulated fixtures matching the brief are included.
- SQLite stores numeric values dynamically; the SQL uses explicit rounding and a small comparison guard. Production systems should use fixed-precision decimal or integer minor units.
- The Excel summary is pivot-equivalent rather than an Excel PivotTable object; it provides the requested discrepancy count by type and direct affected-record references in a portable format.
