#!/usr/bin/env python3
"""Create a deterministic SQLite fixture matching the assignment schema."""
import argparse
import sqlite3
from pathlib import Path

SCHEMA = """
DROP TABLE IF EXISTS Transactions; DROP TABLE IF EXISTS Distributions;
DROP TABLE IF EXISTS SourceCalculations; DROP TABLE IF EXISTS Clients;
CREATE TABLE Clients (client_id TEXT PRIMARY KEY, client_name TEXT NOT NULL, status TEXT NOT NULL, region TEXT NOT NULL);
CREATE TABLE SourceCalculations (calc_id TEXT PRIMARY KEY, client_id TEXT NOT NULL, period TEXT NOT NULL, source_amount NUMERIC NOT NULL, fee_pct NUMERIC, calculated_at TEXT NOT NULL);
CREATE TABLE Distributions (distribution_id TEXT PRIMARY KEY, client_id TEXT NOT NULL, period TEXT NOT NULL, distributed_amount NUMERIC NOT NULL, status TEXT NOT NULL, processed_at TEXT NOT NULL);
CREATE TABLE Transactions (transaction_id TEXT PRIMARY KEY, client_id TEXT NOT NULL, distribution_id TEXT NOT NULL, transaction_type TEXT NOT NULL, amount NUMERIC NOT NULL, status TEXT NOT NULL, transaction_date TEXT NOT NULL);
CREATE INDEX idx_source_client_period ON SourceCalculations(client_id, period);
CREATE INDEX idx_distribution_client_period ON Distributions(client_id, period);
CREATE INDEX idx_transaction_distribution_status ON Transactions(distribution_id, status);
"""


def create_database(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as db:
        db.executescript(SCHEMA)
        db.executemany("INSERT INTO Clients VALUES (?, ?, ?, ?)", [
            ("C001", "Client A", "ACTIVE", "NORTH"), ("C002", "Client B", "ACTIVE", "SOUTH"),
            ("C003", "Client C", "ACTIVE", "WEST"), ("C004", "Client D", "ACTIVE", "EAST"),
            ("C005", "Client E", "ACTIVE", "NORTH")])
        source = [("SC001", "C001", "2026-01", 10000, 2, "2026-01-10"), ("SC002", "C002", "2026-01", 5250.75, 2, "2026-01-10"),
                  ("SC003", "C003", "2026-01", 875, 2, "2026-01-10"), ("SC004", "C004", "2026-01", 800, 2, "2026-01-10"),
                  ("SC005", "C001", "2026-02", 10000, 2, "2026-02-10"), ("SC006", "C002", "2026-02", 5250.75, 2, "2026-02-10"),
                  ("SC007", "C003", "2026-02", 875, 2, "2026-02-10"), ("SC008", "C004", "2026-02", 800, 2, "2026-02-10"),
                  ("SC009", "C001", "2026-03", 10000, 2, "2026-03-10"), ("SC010", "C002", "2026-03", 5250.75, 2, "2026-03-10"),
                  ("SC011", "C003", "2026-03", 875, 2, "2026-03-10"), ("SC012", "C004", "2026-03", 3000, 2, "2026-03-10"),
                  ("SC013", "C005", "2026-03", 840, 2, "2026-03-10")]
        db.executemany("INSERT INTO SourceCalculations VALUES (?, ?, ?, ?, ?, ?)", source)
        amounts = [9800, 5145.74, 857.50, 784, 9800, 5145.76, 857.50, 784, 9800, 5145.74, 857.50, 2940, 823.20]
        distributions = []
        for i, (calc, amount) in enumerate(zip(source, amounts), 1):
            distributions.append((f"D{i:03d}", calc[1], calc[2], amount, "COMPLETED" if i != 13 else "PENDING", calc[5]))
        db.executemany("INSERT INTO Distributions VALUES (?, ?, ?, ?, ?, ?)", distributions)
        tx = []
        for i, dist in enumerate(distributions, 1):
            if dist[0] in {"D012", "D013"}:  # D012 failed; D013 has no transaction.
                if dist[0] == "D012": tx.append(("T012", dist[1], dist[0], "PAYMENT", dist[3], "FAILED", "2026-03-14"))
                continue
            tx.append((f"T{i:03d}", dist[1], dist[0], "PAYMENT", dist[3], "APPROVED", f"{dist[2]}-14"))
        db.executemany("INSERT INTO Transactions VALUES (?, ?, ?, ?, ?, ?, ?)", tx)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--database", type=Path, default=Path("data/distribution_qa.db")); args = parser.parse_args()
    create_database(args.database); print(f"Created {args.database}")
