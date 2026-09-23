import unittest

from incident_agent.models import Incident
from incident_agent.orchestration.model_investigator import ModelInvestigator
from incident_agent.tools.mock import build_mock_gateway


class FakeLocalModel:
    def __init__(self):
        self.calls = 0

    def chat(self, messages, gateway, include_tools=True):
        self.calls += 1
        if self.calls == 1:
            return {
                "message": {
                    "role": "assistant",
                    "tool_calls": [
                        {
                            "function": {
                                "name": "get_service_health",
                                "arguments": {"service": "checkout-service"},
                            }
                        }
                    ],
                }
            }
        return {
            "message": {
                "role": "assistant",
                "content": '{"rootCause":"Service degradation","confidence":0.7,"evidence":[{"tool":"get_service_health","finding":"Service is degraded"}],"recommendedActions":[]}',
            }
        }


class ModelInvestigatorTests(unittest.TestCase):
    def test_model_selects_tool_then_returns_cited_structured_result(self):
        gateway = build_mock_gateway()
        investigator = ModelInvestigator(
            gateway, FakeLocalModel(), minimum_evidence_sources=1
        )
        result = investigator.investigate(
            Incident("service is failing", "checkout-service")
        )
        self.assertEqual(result.confidence, 0.7)
        self.assertEqual(result.evidence[0].tool, "get_service_health")
        self.assertEqual(gateway.audit.events[-1]["event"], "diagnosis_generated")
