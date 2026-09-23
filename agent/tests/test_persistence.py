import unittest

from incident_agent.models import (
    Evidence,
    Incident,
    InvestigationResult,
    Recommendation,
)
from incident_agent.persistence import InMemoryRepository


class InMemoryRepositoryTests(unittest.TestCase):
    def test_saved_report_can_be_retrieved_by_investigation_id(self):
        repository = InMemoryRepository()
        incident = Incident("Checkout is returning HTTP 500", "checkout-service")
        result = InvestigationResult(
            incident=incident,
            root_cause="Database connection pool exhaustion",
            confidence=0.91,
            evidence=(
                Evidence(
                    "database", "All connections are active", "database_diagnostics"
                ),
            ),
            recommendations=(
                Recommendation("Increase the pool size", "Restore capacity"),
            ),
        )

        investigation_id = repository.save(incident, result, [])
        report = repository.get_report(investigation_id)

        self.assertIsNotNone(report)
        self.assertEqual(report["investigationId"], investigation_id)
        self.assertEqual(report["rootCause"], "Database connection pool exhaustion")
        self.assertEqual(report["evidence"][0]["source"], "database")
        self.assertEqual(
            report["recommendations"][0]["action"], "Increase the pool size"
        )
        self.assertIn("createdAt", report)

    def test_missing_report_returns_none(self):
        self.assertIsNone(InMemoryRepository().get_report(99))


if __name__ == "__main__":
    unittest.main()
