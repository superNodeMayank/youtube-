import unittest
from unittest.mock import MagicMock, patch
from datetime import datetime

from src import crud, models, schemas

class TestCrudAIEdits(unittest.TestCase):

    def setUp(self):
        self.mock_db_session = MagicMock()

    @patch('src.crud.get_comment') # Mocks get_comment used within create_ai_comment_edit
    def test_create_ai_comment_edit(self, mock_get_comment):
        comment_id = 1
        user_id = 1 # Assume this is the comment author

        ai_edit_data = schemas.AICommentEditDBInput(
            comment_id=comment_id,
            user_id=user_id,
            raw_comment_text_before_ai="Original text",
            ai_generated_text="AI suggestion",
            status="suggested",
            ai_model_used="gemini-pro"
        )

        # Mock that the associated comment exists and user_id matches
        mock_get_comment.return_value = models.Comment(
            comment_id=comment_id, user_id=user_id, original_text="Original text", video_id=1
        )

        created_ai_edit = crud.create_ai_comment_edit(self.mock_db_session, ai_edit_data)

        args, _ = self.mock_db_session.add.call_args
        added_ai_edit_instance = args[0]

        self.assertIsInstance(added_ai_edit_instance, models.AICommentEdit)
        self.assertEqual(added_ai_edit_instance.comment_id, comment_id)
        self.assertEqual(added_ai_edit_instance.user_id, user_id)
        self.assertEqual(added_ai_edit_instance.raw_comment_text_before_ai, ai_edit_data.raw_comment_text_before_ai)
        self.assertEqual(added_ai_edit_instance.ai_generated_text, ai_edit_data.ai_generated_text)
        self.assertEqual(added_ai_edit_instance.status, "suggested")

        self.mock_db_session.add.assert_called_once_with(added_ai_edit_instance)
        self.mock_db_session.commit.assert_called_once()
        self.mock_db_session.refresh.assert_called_once_with(added_ai_edit_instance)
        self.assertEqual(created_ai_edit, added_ai_edit_instance)
        mock_get_comment.assert_called_once_with(self.mock_db_session, comment_id)

    @patch('src.crud.get_comment')
    def test_create_ai_comment_edit_comment_not_found(self, mock_get_comment):
        mock_get_comment.return_value = None # Simulate comment not found
        ai_edit_data = schemas.AICommentEditDBInput(
            comment_id=999, user_id=1, raw_comment_text_before_ai="t", ai_generated_text="ai", status="s"
        )
        with self.assertRaises(ValueError) as cm:
            crud.create_ai_comment_edit(self.mock_db_session, ai_edit_data)
        self.assertIn("Comment with id 999 not found", str(cm.exception))

    @patch('src.crud.get_comment')
    def test_create_ai_comment_edit_user_mismatch(self, mock_get_comment):
        comment_id = 1
        comment_author_id = 1
        ai_edit_user_id = 2 # Different user

        mock_get_comment.return_value = models.Comment(
            comment_id=comment_id, user_id=comment_author_id, original_text="text", video_id=1
        )
        ai_edit_data = schemas.AICommentEditDBInput(
            comment_id=comment_id, user_id=ai_edit_user_id,
            raw_comment_text_before_ai="t", ai_generated_text="ai", status="s"
        )
        with self.assertRaises(ValueError) as cm:
            crud.create_ai_comment_edit(self.mock_db_session, ai_edit_data)
        self.assertIn(f"User ID {ai_edit_user_id} does not match comment author ID {comment_author_id}", str(cm.exception))


    def test_get_ai_comment_edit(self):
        edit_id = 1
        expected_ai_edit = models.AICommentEdit(
            edit_id=edit_id, comment_id=1, user_id=1,
            raw_comment_text_before_ai="t", ai_generated_text="ai", status="suggested"
        )
        self.mock_db_session.get.return_value = expected_ai_edit

        ai_edit = crud.get_ai_comment_edit(self.mock_db_session, edit_id)

        self.assertEqual(ai_edit, expected_ai_edit)
        self.mock_db_session.get.assert_called_once_with(models.AICommentEdit, edit_id)

    def test_get_latest_ai_suggestion_for_comment(self):
        comment_id = 1
        expected_suggestion = models.AICommentEdit(
            edit_id=2, comment_id=comment_id, user_id=1, status="suggested",
            raw_comment_text_before_ai="t", ai_generated_text="latest_ai",
            api_call_timestamp=datetime.utcnow()
        )

        mock_exec_result = MagicMock()
        mock_exec_result.first.return_value = expected_suggestion
        self.mock_db_session.exec.return_value = mock_exec_result

        suggestion = crud.get_latest_ai_suggestion_for_comment(self.mock_db_session, comment_id)

        self.assertEqual(suggestion, expected_suggestion)
        self.mock_db_session.exec.assert_called_once()
        # We could add assertions here about the select statement filtering by status='suggested' and ordering

    def test_update_ai_comment_edit_status(self):
        edit_id = 1
        new_status = "accepted_as_is"
        user_final_text = "User edited this."

        existing_ai_edit = models.AICommentEdit(
            edit_id=edit_id, comment_id=1, user_id=1, status="suggested",
            raw_comment_text_before_ai="t", ai_generated_text="ai"
        )
        self.mock_db_session.get.return_value = existing_ai_edit

        updated_ai_edit = crud.update_ai_comment_edit_status(
            self.mock_db_session, edit_id, new_status, user_final_text
        )

        self.assertIsNotNone(updated_ai_edit)
        self.assertEqual(updated_ai_edit.status, new_status)
        self.assertEqual(updated_ai_edit.user_final_edited_text, user_final_text)

        self.mock_db_session.add.assert_called_once_with(existing_ai_edit)
        self.mock_db_session.commit.assert_called_once()
        self.mock_db_session.refresh.assert_called_once_with(existing_ai_edit)

    def test_update_ai_comment_edit_status_not_found(self):
        edit_id = 99
        self.mock_db_session.get.return_value = None

        updated_ai_edit = crud.update_ai_comment_edit_status(self.mock_db_session, edit_id, "accepted")

        self.assertIsNone(updated_ai_edit)
        self.mock_db_session.add.assert_not_called()

if __name__ == '__main__':
    unittest.main()
