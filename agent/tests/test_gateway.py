import unittest

from incident_agent.tools.gateway import ToolDenied
from incident_agent.tools.mock import build_mock_gateway


class ToolGatewayTests(unittest.TestCase):
    def test_read_tool_is_callable_and_audited(self):
        gateway = build_mock_gateway()
        result = gateway.call("get_service_health", service="checkout-service")
        self.assertEqual(result["status"], "degraded")
        self.assertEqual(gateway.audit.events[-1]["event"], "tool_call_succeeded")

    def test_write_tool_requires_approval(self):
        gateway = build_mock_gateway()
        with self.assertRaises(ToolDenied):
            gateway.call("rollback_deployment", deployment_id="184")
        self.assertEqual(gateway.audit.events[-1]["reason"], "approval_required")

    def test_unknown_tool_is_rejected(self):
        gateway = build_mock_gateway()
        with self.assertRaises(ToolDenied):
            gateway.call("run_shell", command="rm -rf /")
