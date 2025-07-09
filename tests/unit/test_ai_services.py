import unittest
from unittest.mock import patch, MagicMock, PropertyMock

# Before importing ai_services, set up mocks for google.generativeai
# This is to prevent actual API calls or config errors during test discovery/setup
mock_genai = MagicMock()
mock_generative_model = MagicMock()

# Mock the model instance that genai.GenerativeModel() would return
mock_model_instance = MagicMock()
mock_genai.GenerativeModel.return_value = mock_model_instance

# Patch 'google.generativeai' before it's imported by src.ai_services
# Also patch settings if GEMINI_API_KEY is read at module level
# For simplicity, assume settings are loaded correctly and GEMINI_API_KEY is present for these tests
# or mock settings.GEMINI_API_KEY directly.

# If settings are accessed at module level in ai_services, ensure they are patched early.
# from src.config import settings # This would load actual settings
# Instead, we can patch 'src.ai_services.settings' if needed, or ensure ai_services uses a passed-in config.
# For now, we assume ai_services.settings.GEMINI_API_KEY is valid for tests focusing on logic after init.

# It's often cleaner to patch specific objects *within* the module under test rather than the global import.
# However, for external libraries like 'google.generativeai' that are configured at module load,
# patching early or at module level is common.

# Let's try patching where 'genai' is used inside 'ai_services'
# This means we need to patch 'src.ai_services.genai'

@patch('src.ai_services.settings') # Patch settings used by ai_services
@patch('src.ai_services.genai', new=mock_genai) # Patch the genai module object within ai_services
class TestAIServices(unittest.TestCase):

    def setUp(self):
        # Reset mocks before each test
        mock_genai.reset_mock()
        mock_generative_model.reset_mock() # This is an alias for mock_genai.GenerativeModel
        mock_model_instance.reset_mock()

        # Ensure the model is "initialized" for tests that need it
        # This simulates successful model initialization in ai_services
        # If ai_services.model is directly used:
        # from src import ai_services
        # ai_services.model = mock_model_instance
        # However, it's better if ai_services.enhance_comment_with_ai checks/uses its 'model' variable

    def test_enhance_comment_successful(self, mock_settings):
        # Mock settings to have API key
        mock_settings.GEMINI_API_KEY = "fake_key"

        # Import here, after patches are set up
        from src import ai_services
        ai_services.model = mock_model_instance # Ensure the service uses our mock model

        raw_comment = "This is a test comment."
        expected_enhanced_comment = "This is an enhanced test comment."

        # Mock the response from model.generate_content()
        mock_response = MagicMock()
        mock_candidate = MagicMock()
        mock_part = MagicMock()
        mock_part.text = expected_enhanced_comment
        mock_candidate.content.parts = [mock_part]
        mock_candidate.finish_reason.name = "STOP" # Simulate normal finish
        mock_response.candidates = [mock_candidate]
        mock_response.prompt_feedback.block_reason = None # No blocking

        mock_model_instance.generate_content.return_value = mock_response

        enhanced_comment = ai_services.enhance_comment_with_ai(raw_comment)

        self.assertEqual(enhanced_comment, expected_enhanced_comment)
        mock_model_instance.generate_content.assert_called_once()
        # We could also assert the prompt structure if needed:
        # called_prompt = mock_model_instance.generate_content.call_args[0][0]
        # self.assertIn(raw_comment, called_prompt)


    def test_enhance_comment_api_error(self, mock_settings):
        mock_settings.GEMINI_API_KEY = "fake_key"
        from src import ai_services
        ai_services.model = mock_model_instance

        raw_comment = "Another test comment."
        mock_model_instance.generate_content.side_effect = Exception("Simulated API error")

        enhanced_comment = ai_services.enhance_comment_with_ai(raw_comment)

        self.assertIsNone(enhanced_comment)
        mock_model_instance.generate_content.assert_called_once()

    def test_enhance_comment_empty_input(self, mock_settings):
        mock_settings.GEMINI_API_KEY = "fake_key"
        from src import ai_services
        ai_services.model = mock_model_instance

        enhanced_comment = ai_services.enhance_comment_with_ai("")
        self.assertIsNone(enhanced_comment) # Or "" depending on implementation
        mock_model_instance.generate_content.assert_not_called()

    def test_enhance_comment_model_not_initialized(self, mock_settings):
        mock_settings.GEMINI_API_KEY = "fake_key" # Key is there
        from src import ai_services
        ai_services.model = None # Simulate model failing to initialize

        raw_comment = "Test comment for uninitialized model."
        enhanced_comment = ai_services.enhance_comment_with_ai(raw_comment)

        self.assertIsNone(enhanced_comment)
        mock_model_instance.generate_content.assert_not_called() # Ensure it doesn't try to use None model

    def test_enhance_comment_no_api_key(self, mock_settings):
        # Simulate GEMINI_API_KEY being None *when ai_services module is loaded/configured*
        # This is tricky because ai_services configures genai at module level.
        # For this test, we'd ideally reload ai_services with the setting patched.
        # A simpler way for this specific unit test is to check the behavior if 'model' is None.
        # This was covered by test_enhance_comment_model_not_initialized

        # If we want to test the logger warning for no API key:
        # This requires re-importing or using importlib.reload after patching settings.
        # For now, we assume the module-level configuration logic is simple and focus on the function.
        mock_settings.GEMINI_API_KEY = None # API Key is None
        from src import ai_services
        import importlib
        importlib.reload(ai_services) # Reload to re-trigger genai.configure and model init with no key

        # After reload, ai_services.model should be None
        self.assertIsNone(ai_services.model, "Model should be None if API key is missing at module load.")

        raw_comment = "Test with no API key."
        enhanced_comment = ai_services.enhance_comment_with_ai(raw_comment)
        self.assertIsNone(enhanced_comment)


    def test_enhance_comment_prompt_blocked(self, mock_settings):
        mock_settings.GEMINI_API_KEY = "fake_key"
        from src import ai_services
        ai_services.model = mock_model_instance

        raw_comment = "A comment that might be blocked."

        mock_response = MagicMock()
        # Simulate no candidates and a block reason
        mock_response.candidates = []
        # type(mock_response.prompt_feedback).block_reason = PropertyMock(return_value="SAFETY") # More robust
        mock_response.prompt_feedback = MagicMock()
        mock_response.prompt_feedback.block_reason = "SAFETY"


        mock_model_instance.generate_content.return_value = mock_response

        enhanced_comment = ai_services.enhance_comment_with_ai(raw_comment)
        self.assertIsNone(enhanced_comment)
        mock_model_instance.generate_content.assert_called_once()

    def test_enhance_comment_finish_reason_safety(self, mock_settings):
        mock_settings.GEMINI_API_KEY = "fake_key"
        from src import ai_services
        ai_services.model = mock_model_instance

        raw_comment = "Comment leading to safety stop."

        mock_response = MagicMock()
        mock_candidate = MagicMock()
        # Candidate has content, but finish reason is SAFETY
        mock_part = MagicMock()
        mock_part.text = "Potentially unsafe completion."
        mock_candidate.content.parts = [mock_part]
        mock_candidate.finish_reason.name = "SAFETY"
        mock_response.candidates = [mock_candidate]
        mock_response.prompt_feedback.block_reason = None

        mock_model_instance.generate_content.return_value = mock_response

        enhanced_comment = ai_services.enhance_comment_with_ai(raw_comment)
        self.assertIsNone(enhanced_comment, "Should return None if finish reason is SAFETY")

    def test_enhance_comment_custom_prompt(self, mock_settings):
        mock_settings.GEMINI_API_KEY = "fake_key"
        from src import ai_services
        ai_services.model = mock_model_instance

        raw_comment = "Test comment."
        custom_template = "Make this funny: {comment}"
        expected_prompt = custom_template.format(comment=raw_comment)
        expected_enhanced = "Funny version of test comment."

        mock_response = MagicMock()
        mock_candidate = MagicMock()
        mock_part = MagicMock()
        mock_part.text = expected_enhanced
        mock_candidate.content.parts = [mock_part]
        mock_candidate.finish_reason.name = "STOP"
        mock_response.candidates = [mock_candidate]
        mock_response.prompt_feedback.block_reason = None
        mock_model_instance.generate_content.return_value = mock_response

        enhanced = ai_services.enhance_comment_with_ai(raw_comment, user_prompt_template=custom_template)
        self.assertEqual(enhanced, expected_enhanced)

        # Check that the correct prompt was used
        called_args, _ = mock_model_instance.generate_content.call_args
        self.assertEqual(called_args[0], expected_prompt)

    def test_enhance_comment_custom_prompt_missing_placeholder(self, mock_settings):
        mock_settings.GEMINI_API_KEY = "fake_key"
        from src import ai_services
        ai_services.model = mock_model_instance

        raw_comment = "Test comment."
        invalid_template = "Make this funny (no placeholder)" # Missing {comment}
        # Should fall back to default prompt
        expected_default_prompt_segment = f"Original comment: \"{raw_comment}\""


        mock_response = MagicMock() # Standard successful response
        mock_candidate = MagicMock()
        mock_part = MagicMock(); mock_part.text = "Some enhancement"
        mock_candidate.content.parts = [mock_part]; mock_candidate.finish_reason.name = "STOP"
        mock_response.candidates = [mock_candidate]; mock_response.prompt_feedback.block_reason = None
        mock_model_instance.generate_content.return_value = mock_response

        ai_services.enhance_comment_with_ai(raw_comment, user_prompt_template=invalid_template)

        called_args, _ = mock_model_instance.generate_content.call_args
        self.assertIn(expected_default_prompt_segment, called_args[0], "Should use default prompt if template is invalid.")


if __name__ == '__main__':
    unittest.main()
