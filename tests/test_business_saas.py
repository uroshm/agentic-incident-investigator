import unittest

from services.business_saas.server import DatabasePoolExhaustedError, SCENARIO_NAME, SaaSState


class SaaSStateTests(unittest.TestCase):
    def test_incident_toggle_changes_service_state(self):
        state = SaaSState()
        self.assertEqual(state.snapshot()["status"], "healthy")

        state.toggle_incident(True)
        snapshot = state.snapshot()
        self.assertEqual(snapshot["status"], "degraded")
        self.assertEqual(snapshot["incident"], SCENARIO_NAME)
        self.assertEqual(snapshot["db_connections_active"], snapshot["db_connections_max"])

        state.toggle_incident(False)
        self.assertEqual(state.snapshot()["status"], "healthy")

    def test_manual_request_creates_failure_during_incident(self):
        state = SaaSState()
        state.toggle_incident(True)
        with self.assertRaises(DatabasePoolExhaustedError):
            state.simulate_request()
        snapshot = state.snapshot()
        self.assertEqual(snapshot["requests_total"], 1)
        self.assertEqual(snapshot["errors_total"], 1)
