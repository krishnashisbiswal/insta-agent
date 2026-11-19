import os
import unittest
from unittest.mock import MagicMock, patch
import pytest

from app.agents import gemini_client
from app.autonomous.daily_algorithm_publisher import DailyAlgorithmPublisher
from app.agents.caption_agent import optimize_caption
from app.agents.script_agent import generate_reel
from app.video.cinematic_composer import create_cinematic_reel_video
from app.storage.permanent_visual_memory import PermanentVisualMemory


class TestCIImportsWithoutSecrets(unittest.TestCase):
    """
    Verifies that critical application modules can be safely imported
    without requiring GEMINI_API_KEY or other external credentials in CI/CD.
    """

    def test_gemini_client_import_has_no_side_effects(self):
        """Importing gemini_client must not raise an exception even if GEMINI_API_KEY is empty."""
        with patch.dict(os.environ, {"GEMINI_API_KEY": ""}, clear=False):
            # Reset the cached client to test lazy initialization
            gemini_client._client = None
            self.assertIsNone(gemini_client._client)

    def test_get_client_raises_actionable_error_when_unconfigured(self):
        """Calling get_client() without a key raises a clear, actionable RuntimeError."""
        with patch.dict(os.environ, {"GEMINI_API_KEY": ""}, clear=False):
            with patch.object(gemini_client, "GEMINI_API_KEY", ""):
                gemini_client._client = None
                with pytest.raises(RuntimeError) as exc_info:
                    gemini_client.get_client()
                self.assertIn("GEMINI_API_KEY is missing", str(exc_info.value))

    def test_gemini_functions_work_with_mocked_client(self):
        """Verify generate_text works normally when the client is mocked without external requests."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = '{"status": "ok", "message": "mocked test"}'
        mock_client.models.generate_content.return_value = mock_response

        with patch.object(gemini_client, "get_client", return_value=mock_client):
            res_text = gemini_client.generate_text("Test prompt")
            self.assertEqual(res_text, '{"status": "ok", "message": "mocked test"}')

            res_json = gemini_client.generate_json("Test JSON prompt")
            self.assertEqual(res_json, {"status": "ok", "message": "mocked test"})

    def test_daily_algorithm_publisher_imports_cleanly(self):
        """DailyAlgorithmPublisher can be instantiated and validated without credentials in dry-run mode."""
        with patch.dict(os.environ, {"GEMINI_API_KEY": ""}, clear=False):
            env_status = DailyAlgorithmPublisher.validate_environment(dry_run=True)
            self.assertTrue(env_status["dry_run"])
            self.assertTrue(env_status["valid"])
