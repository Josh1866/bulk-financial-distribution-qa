-- Q1: Distribution records with no corresponding APPROVED transaction.
-- Linking on distribution_id prevents a different payment for the same client from masking the gap.
SELECT d.distribution_id, d.client_id, c.client_name, d.period,
       ROUND(d.distributed_amount, 2) AS distributed_amount, d.status AS distribution_status
FROM Distributions d
JOIN Clients c ON c.client_id = d.client_id
WHERE NOT EXISTS (
    SELECT 1 FROM Transactions t
    WHERE t.distribution_id = d.distribution_id AND t.client_id = d.client_id AND t.status = 'APPROVED'
)
ORDER BY d.period, d.client_id;

-- Q2: Total distributed amount by month for the covered period.
SELECT substr(period, 1, 7) AS distribution_month,
       COUNT(*) AS distribution_count,
       ROUND(SUM(distributed_amount), 2) AS total_distributed_amount
FROM Distributions
GROUP BY substr(period, 1, 7)
ORDER BY distribution_month;

-- Q3: Distributed amount differs from calculated source net by more than $0.01.
-- Expected net is rounded to cents before comparison.
WITH reconciled AS (
    SELECT d.distribution_id, d.client_id, c.client_name, d.period,
           ROUND(ROUND(s.source_amount * 100 * (100 - s.fee_pct) / 100.0) / 100.0, 2) AS expected_net_amount,
           ROUND(d.distributed_amount, 2) AS distributed_amount,
           ROUND(d.distributed_amount - ROUND(s.source_amount * 100 * (100 - s.fee_pct) / 100.0) / 100.0, 2) AS variance
    FROM Distributions d
    JOIN SourceCalculations s ON s.client_id = d.client_id AND s.period = d.period
    JOIN Clients c ON c.client_id = d.client_id
)
SELECT * FROM reconciled
WHERE ABS(variance) > 0.0100001
ORDER BY period, client_id;
