import unittest
from unittest.mock import MagicMock, patch
from datetime import datetime

from src import crud, models, schemas

class TestCrudAIEnhancementLogs(unittest.TestCase): # Renamed class

    def setUp(self):
        self.mock_db_session = MagicMock()

    @patch('src.crud.get_comment') # Mocks get_comment used within create_ai_enhancement_log
    def test_create_ai_enhancement_log(self, mock_get_comment): # Renamed method
        comment_id = 1
        user_id = 1 # Assume this is the comment author

        log_data = schemas.AIEnhancementLogDBInput( # Updated schema name
            comment_id=comment_id,
            user_id=user_id,
            raw_comment_text_before_ai="Original text",
            ai_generated_text="AI suggestion",
            status="suggested",
            ai_model_used="gemini-pro"
        )

        mock_get_comment.return_value = models.Comment(
            comment_id=comment_id, user_id=user_id, original_text="Original text", video_id=1
        )

        created_log_entry = crud.create_ai_enhancement_log(self.mock_db_session, log_data) # Updated function call

        args, _ = self.mock_db_session.add.call_args
        added_log_instance = args[0] # Renamed variable

        self.assertIsInstance(added_log_instance, models.AIEnhancementLog) # Updated model name
        self.assertEqual(added_log_instance.comment_id, comment_id)
        self.assertEqual(added_log_instance.user_id, user_id)
        self.assertEqual(added_log_instance.raw_comment_text_before_ai, log_data.raw_comment_text_before_ai)
        self.assertEqual(added_log_instance.ai_generated_text, log_data.ai_generated_text)
        self.assertEqual(added_log_instance.status, "suggested")

        self.mock_db_session.add.assert_called_once_with(added_log_instance)
        self.mock_db_session.commit.assert_called_once()
        self.mock_db_session.refresh.assert_called_once_with(added_log_instance)
        self.assertEqual(created_log_entry, added_log_instance)
        mock_get_comment.assert_called_once_with(self.mock_db_session, comment_id)

    @patch('src.crud.get_comment')
    def test_create_ai_enhancement_log_comment_not_found(self, mock_get_comment): # Renamed
        mock_get_comment.return_value = None
        log_data = schemas.AIEnhancementLogDBInput( # Updated schema
            comment_id=999, user_id=1, raw_comment_text_before_ai="t", ai_generated_text="ai", status="s"
        )
        with self.assertRaises(ValueError) as cm:
            crud.create_ai_enhancement_log(self.mock_db_session, log_data) # Updated function
        self.assertIn("Comment with id 999 not found", str(cm.exception))

    @patch('src.crud.get_comment')
    def test_create_ai_enhancement_log_user_mismatch(self, mock_get_comment): # Renamed
        comment_id = 1
        comment_author_id = 1
        log_user_id = 2 # Different user for the log entry

        mock_get_comment.return_value = models.Comment(
            comment_id=comment_id, user_id=comment_author_id, original_text="text", video_id=1
        )
        log_data = schemas.AIEnhancementLogDBInput( # Updated schema
            comment_id=comment_id, user_id=log_user_id,
            raw_comment_text_before_ai="t", ai_generated_text="ai", status="s"
        )
        with self.assertRaises(ValueError) as cm:
            crud.create_ai_enhancement_log(self.mock_db_session, log_data) # Updated function
        self.assertIn(f"User ID {log_user_id} does not match comment author ID {comment_author_id}", str(cm.exception))


    def test_get_ai_enhancement_log(self): # Renamed
        log_id = 1 # Updated variable name
        expected_log_entry = models.AIEnhancementLog( # Updated model
            log_id=log_id, comment_id=1, user_id=1,
            raw_comment_text_before_ai="t", ai_generated_text="ai", status="suggested"
        )
        self.mock_db_session.get.return_value = expected_log_entry

        log_entry = crud.get_ai_enhancement_log(self.mock_db_session, log_id) # Updated function

        self.assertEqual(log_entry, expected_log_entry)
        self.mock_db_session.get.assert_called_once_with(models.AIEnhancementLog, log_id) # Updated model

    def test_get_latest_ai_suggestion_for_comment(self): # Name is still relevant
        comment_id = 1
        expected_suggestion = models.AIEnhancementLog( # Updated model
            log_id=2, comment_id=comment_id, user_id=1, status="suggested",
            raw_comment_text_before_ai="t", ai_generated_text="latest_ai",
            api_call_timestamp=datetime.utcnow()
        )

        mock_exec_result = MagicMock()
        mock_exec_result.first.return_value = expected_suggestion
        self.mock_db_session.exec.return_value = mock_exec_result

        suggestion = crud.get_latest_ai_suggestion_for_comment(self.mock_db_session, comment_id)

        self.assertEqual(suggestion, expected_suggestion)
        self.mock_db_session.exec.assert_called_once()

    def test_update_ai_enhancement_log_status(self): # Renamed
        log_id = 1 # Updated variable name
        new_status = "accepted_as_is"
        user_final_text = "User edited this."

        existing_log_entry = models.AIEnhancementLog( # Updated model
            log_id=log_id, comment_id=1, user_id=1, status="suggested",
            raw_comment_text_before_ai="t", ai_generated_text="ai"
        )
        self.mock_db_session.get.return_value = existing_log_entry

        updated_log_entry = crud.update_ai_enhancement_log_status( # Updated function
            self.mock_db_session, log_id, new_status, user_final_text
        )

        self.assertIsNotNone(updated_log_entry)
        self.assertEqual(updated_log_entry.status, new_status)
        self.assertEqual(updated_log_entry.user_final_edited_text, user_final_text)

        self.mock_db_session.add.assert_called_once_with(existing_log_entry)
        self.mock_db_session.commit.assert_called_once()
        self.mock_db_session.refresh.assert_called_once_with(existing_log_entry)

    def test_update_ai_enhancement_log_status_not_found(self): # Renamed
        log_id = 99 # Updated variable name
        self.mock_db_session.get.return_value = None

        updated_log_entry = crud.update_ai_enhancement_log_status(self.mock_db_session, log_id, "accepted") # Updated function

        self.assertIsNone(updated_log_entry)
        self.mock_db_session.add.assert_not_called()

if __name__ == '__main__':
    unittest.main()
