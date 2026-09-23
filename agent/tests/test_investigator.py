import unittest

from incident_agent.models import Incident
from incident_agent.orchestration.investigator import Investigator
from incident_agent.tools.mock import build_mock_gateway


class InvestigatorTests(unittest.TestCase):
    def test_baseline_investigation_returns_evidence_and_recommendations(self):
        gateway = build_mock_gateway()
        result = Investigator(gateway).investigate(
            Incident("checkout is failing", "checkout-service")
        )
        self.assertIn("connection pool exhaustion", result.root_cause)
        self.assertGreaterEqual(len(result.evidence), 8)
        self.assertTrue(all(item.requires_approval for item in result.recommendations))
        self.assertEqual(gateway.audit.events[0]["event"], "investigation_started")
        self.assertEqual(gateway.audit.events[-2]["event"], "hypothesis_selected")
        self.assertEqual(gateway.audit.events[-1]["event"], "diagnosis_generated")
