import os
import unittest
from unittest.mock import patch

try:
    from . import llm_service
except ImportError:
    import llm_service


class LocalTriageTests(unittest.TestCase):
    @patch.dict(os.environ, {"LLM_API_KEY": ""})
    def test_hazardous_report_uses_explicit_local_fallback(self) -> None:
        result = llm_service.triage_citizen_report("Broken glass beside the school gate", "medium")

        self.assertEqual(result["wasteType"], "Hazardous")
        self.assertEqual(result["urgency"], "high")
        self.assertEqual(result["source"], "local_rules")
        self.assertTrue(result["warning"])

    @patch.dict(os.environ, {"LLM_API_KEY": ""})
    def test_high_citizen_urgency_is_preserved(self) -> None:
        result = llm_service.triage_citizen_report("Food waste in a closed collection bin", "high")

        self.assertEqual(result["wasteType"], "Organic")
        self.assertEqual(result["urgency"], "high")
        self.assertGreaterEqual(result["priorityScore"], 82)

    @patch.dict(os.environ, {"LLM_API_KEY": "test-key"})
    def test_invalid_cloud_classification_falls_back_to_rules(self) -> None:
        with patch.object(llm_service, "_chat", return_value=(
            '{"wasteType":"Unknown","urgency":"medium","priorityScore":40,'
            '"estimatedWasteKg":15,"handlingInstructions":"Use standard collection procedure."}'
        )):
            result = llm_service.triage_citizen_report("Plastic bottles by the bus stop", "low")

        self.assertEqual(result["wasteType"], "Recyclable")
        self.assertEqual(result["source"], "local_rules")
        self.assertTrue(result["warning"])


if __name__ == "__main__":
    unittest.main()
