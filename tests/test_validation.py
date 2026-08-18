import sys, unittest
from decimal import Decimal
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from validate_distributions import load_csv, money, reconcile


class ValidationTests(unittest.TestCase):
    def test_money_uses_half_up_cent_rounding(self): self.assertEqual(money(Decimal("1.005")), Decimal("1.01"))
    def test_sample_findings_are_complete_and_categorised(self):
        root = Path(__file__).resolve().parents[1]
        findings = reconcile(load_csv(root / "data/source_calculations.csv"), load_csv(root / "data/distribution_output.csv"))
        self.assertEqual({f["client_id"] for f in findings}, {"C002", "C005", "C007", "C011", "C013"})
        self.assertEqual(len(findings), 5)
        by_id = {f["client_id"]: f for f in findings}
        self.assertEqual(by_id["C002"]["variance"], "-0.01")
        self.assertEqual(by_id["C011"]["discrepancy_type"], "Calculation / business-rule error")


if __name__ == "__main__": unittest.main()
