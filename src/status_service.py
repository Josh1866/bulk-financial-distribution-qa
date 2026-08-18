#!/usr/bin/env python3
"""Locally simulated status-check service with a replaceable repository boundary."""
from __future__ import annotations
import json, re, sys
from dataclasses import asdict, dataclass
from decimal import Decimal


class ValidationError(ValueError): pass
class DistributionNotFound(LookupError): pass


@dataclass(frozen=True)
class DistributionStatus:
    client_id: str
    period: str
    status: str
    distributed_amount: str


class InMemoryDistributionRepository:
    def __init__(self, records=None):
        self.records = records or {
            ("C001", "2026-06"): ("COMPLETED", Decimal("9800.00")),
            ("C002", "2026-06"): ("PENDING", Decimal("0.00")),
            ("C003", "2026-06"): ("FAILED", Decimal("0.00")),
        }

    def find(self, client_id, period): return self.records.get((client_id, period))


class DistributionStatusService:
    VALID_STATUSES = {"PENDING", "COMPLETED", "FAILED"}
    def __init__(self, repository): self.repository = repository

    def get_status(self, client_id: str, period: str) -> DistributionStatus:
        if not client_id or not re.fullmatch(r"C\d{3,}", client_id): raise ValidationError("client_id must match C followed by at least 3 digits")
        if not period or not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", period): raise ValidationError("period must use YYYY-MM")
        record = self.repository.find(client_id, period)
        if record is None: raise DistributionNotFound(f"No distribution found for {client_id} in {period}")
        status, amount = record
        if status not in self.VALID_STATUSES: raise ValidationError(f"Unsupported status: {status}")
        return DistributionStatus(client_id, period, status, f"{amount:.2f}")


if __name__ == "__main__":
    try:
        result = DistributionStatusService(InMemoryDistributionRepository()).get_status(*sys.argv[1:3]); print(json.dumps(asdict(result)))
    except (ValidationError, DistributionNotFound, IndexError) as exc:
        print(json.dumps({"error": str(exc)})); raise SystemExit(2)
