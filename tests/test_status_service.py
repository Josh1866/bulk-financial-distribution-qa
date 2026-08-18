import sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from status_service import DistributionNotFound, DistributionStatusService, InMemoryDistributionRepository, ValidationError


class DistributionStatusRegressionTests(unittest.TestCase):
    def setUp(self): self.service = DistributionStatusService(InMemoryDistributionRepository())
    def test_completed_distribution(self):
        result = self.service.get_status("C001", "2026-06"); self.assertEqual((result.status, result.distributed_amount), ("COMPLETED", "9800.00"))
    def test_pending_distribution(self):
        result = self.service.get_status("C002", "2026-06"); self.assertEqual((result.status, result.distributed_amount), ("PENDING", "0.00"))
    def test_failed_distribution(self):
        result = self.service.get_status("C003", "2026-06"); self.assertEqual((result.status, result.distributed_amount), ("FAILED", "0.00"))
    def test_invalid_client_id_not_found(self):
        with self.assertRaises(DistributionNotFound): self.service.get_status("C999", "2026-06")
    def test_missing_period_is_rejected(self):
        with self.assertRaisesRegex(ValidationError, "YYYY-MM"): self.service.get_status("C001", "")


if __name__ == "__main__": unittest.main()
