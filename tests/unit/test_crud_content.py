import unittest
from unittest.mock import MagicMock, patch
from datetime import datetime

from src import crud, models, schemas # models and schemas needed for type hints and object creation

class TestCrudContent(unittest.TestCase):

    def setUp(self):
        self.mock_db_session = MagicMock()

    # --- Video CRUD Tests ---
    def test_get_video(self):
        video_id = 1
        expected_video = models.Video(video_id=video_id, title="Test Video", url="http://example.com/video1", uploader_user_id=1)
        self.mock_db_session.get.return_value = expected_video

        video = crud.get_video(self.mock_db_session, video_id)
        self.assertEqual(video, expected_video)
        self.mock_db_session.get.assert_called_once_with(models.Video, video_id)

    def test_create_video(self):
        video_data = schemas.VideoCreate(title="New Video", url="http://example.com/new_video", uploader_user_id=1)

        # crud.create_video uses models.Video.model_validate(video_data)
        # The instance returned by model_validate is what's added and refreshed.

        created_video = crud.create_video(self.mock_db_session, video_data)

        args, _ = self.mock_db_session.add.call_args
        added_video_instance = args[0]

        self.assertIsInstance(added_video_instance, models.Video)
        self.assertEqual(added_video_instance.title, video_data.title)
        self.assertEqual(added_video_instance.url, video_data.url)
        self.assertEqual(added_video_instance.uploader_user_id, video_data.uploader_user_id)

        self.mock_db_session.add.assert_called_once_with(added_video_instance)
        self.mock_db_session.commit.assert_called_once()
        self.mock_db_session.refresh.assert_called_once_with(added_video_instance)
        self.assertEqual(created_video, added_video_instance)

    def test_get_videos(self):
        expected_videos = [
            models.Video(video_id=1, title="V1", url="u1", uploader_user_id=1),
            models.Video(video_id=2, title="V2", url="u2", uploader_user_id=1)
        ]
        mock_exec_result = MagicMock()
        mock_exec_result.all.return_value = expected_videos
        self.mock_db_session.exec.return_value = mock_exec_result

        videos = crud.get_videos(self.mock_db_session, skip=0, limit=10)
        self.assertEqual(videos, expected_videos)
        self.mock_db_session.exec.assert_called_once()


    # --- Comment CRUD Tests ---
    @patch('src.crud.get_video') # Mock get_video used within create_comment
    def test_create_comment(self, mock_get_video):
        user_id = 1
        video_id = 1
        comment_data = schemas.CommentCreateAPI(
            original_text="This is a new comment",
            video_id=video_id
        )

        # Mock that the video exists
        mock_get_video.return_value = models.Video(video_id=video_id, title="Test Video", url="url", uploader_user_id=user_id)

        created_comment = crud.create_comment(self.mock_db_session, comment_data, user_id)

        args, _ = self.mock_db_session.add.call_args
        added_comment_instance = args[0]

        self.assertIsInstance(added_comment_instance, models.Comment)
        self.assertEqual(added_comment_instance.original_text, comment_data.original_text)
        self.assertEqual(added_comment_instance.displayed_text, comment_data.original_text) # Default behavior
        self.assertFalse(added_comment_instance.is_ai_assisted) # Default
        self.assertEqual(added_comment_instance.video_id, video_id)
        self.assertEqual(added_comment_instance.user_id, user_id)

        self.mock_db_session.add.assert_called_once_with(added_comment_instance)
        self.mock_db_session.commit.assert_called_once()
        self.mock_db_session.refresh.assert_called_once_with(added_comment_instance)
        self.assertEqual(created_comment, added_comment_instance)
        mock_get_video.assert_called_once_with(self.mock_db_session, video_id)

    @patch('src.crud.get_video')
    def test_create_comment_video_not_found(self, mock_get_video):
        mock_get_video.return_value = None # Simulate video not found
        comment_data = schemas.CommentCreateAPI(original_text="text", video_id=999)

        with self.assertRaises(ValueError) as cm:
            crud.create_comment(self.mock_db_session, comment_data, user_id=1)
        self.assertIn("Video with id 999 not found", str(cm.exception))

    @patch('src.crud.get_video') # Mock get_video
    @patch('src.crud.get_comment') # Mock get_comment for parent comment check
    def test_create_reply_comment(self, mock_get_parent_comment, mock_get_video):
        user_id = 1
        video_id = 1
        parent_comment_id = 10

        reply_data = schemas.CommentCreateAPI(
            original_text="This is a reply",
            video_id=video_id,
            parent_comment_id=parent_comment_id
        )

        mock_get_video.return_value = models.Video(video_id=video_id, title="V", url="u", uploader_user_id=1)
        mock_get_parent_comment.return_value = models.Comment(
            comment_id=parent_comment_id, original_text="Parent", displayed_text="Parent",
            video_id=video_id, user_id=2 # Parent can be by another user
        )

        created_reply = crud.create_comment(self.mock_db_session, reply_data, user_id)

        self.assertEqual(created_reply.parent_comment_id, parent_comment_id)
        mock_get_parent_comment.assert_called_once_with(self.mock_db_session, parent_comment_id)


    def test_get_comment(self):
        comment_id = 1
        expected_comment = models.Comment(comment_id=comment_id, original_text="Test", displayed_text="Test", video_id=1, user_id=1)
        self.mock_db_session.get.return_value = expected_comment

        comment = crud.get_comment(self.mock_db_session, comment_id)
        self.assertEqual(comment, expected_comment)
        self.mock_db_session.get.assert_called_once_with(models.Comment, comment_id)

    def test_get_comments_for_video(self):
        video_id = 1
        expected_comments = [
            models.Comment(comment_id=1, original_text="C1", displayed_text="C1", video_id=video_id, user_id=1),
            models.Comment(comment_id=2, original_text="C2", displayed_text="C2", video_id=video_id, user_id=2),
        ]
        mock_exec_result = MagicMock()
        mock_exec_result.all.return_value = expected_comments
        self.mock_db_session.exec.return_value = mock_exec_result

        comments = crud.get_comments_for_video(self.mock_db_session, video_id, skip=0, limit=10)
        self.assertEqual(comments, expected_comments)
        # Further assertions could be made on the select statement if needed
        self.mock_db_session.exec.assert_called_once()


    def test_update_comment_text(self):
        comment_id = 1
        user_id = 1 # Author
        new_text = "Updated comment text"

        existing_comment = models.Comment(
            comment_id=comment_id, user_id=user_id, original_text="Original", displayed_text="Original", video_id=1
        )
        self.mock_db_session.get.return_value = existing_comment

        updated_comment = crud.update_comment_text(self.mock_db_session, comment_id, new_text, user_id)

        self.assertIsNotNone(updated_comment)
        self.assertEqual(updated_comment.displayed_text, new_text)
        self.assertEqual(updated_comment.original_text, "Original") # Original text should not change

        self.mock_db_session.add.assert_called_once_with(existing_comment)
        self.mock_db_session.commit.assert_called_once()
        self.mock_db_session.refresh.assert_called_once_with(existing_comment)

    def test_update_comment_text_not_author(self):
        comment_id = 1
        author_id = 1
        updater_id = 2 # Not the author
        new_text = "Attempted update"

        existing_comment = models.Comment(
            comment_id=comment_id, user_id=author_id, original_text="Original", displayed_text="Original", video_id=1
        )
        self.mock_db_session.get.return_value = existing_comment

        updated_comment = crud.update_comment_text(self.mock_db_session, comment_id, new_text, updater_id)

        self.assertIsNone(updated_comment)
        self.mock_db_session.add.assert_not_called()
        self.mock_db_session.commit.assert_not_called()

    def test_delete_comment(self):
        comment_id = 1
        user_id = 1 # Author
        existing_comment = models.Comment(
            comment_id=comment_id, user_id=user_id, original_text="Original", displayed_text="Original", video_id=1, is_deleted=False
        )
        self.mock_db_session.get.return_value = existing_comment

        deleted_comment = crud.delete_comment(self.mock_db_session, comment_id, user_id)

        self.assertIsNotNone(deleted_comment)
        self.assertTrue(deleted_comment.is_deleted)
        self.assertEqual(deleted_comment.displayed_text, "This comment has been deleted.")
        self.mock_db_session.add.assert_called_once_with(existing_comment)
        self.mock_db_session.commit.assert_called_once()
        self.mock_db_session.refresh.assert_called_once_with(existing_comment)

    def test_delete_comment_not_author(self):
        comment_id = 1
        author_id = 1
        deleter_id = 2
        existing_comment = models.Comment(
            comment_id=comment_id, user_id=author_id, original_text="Original", displayed_text="Original", video_id=1, is_deleted=False
        )
        self.mock_db_session.get.return_value = existing_comment

        deleted_comment = crud.delete_comment(self.mock_db_session, comment_id, deleter_id)
        self.assertIsNone(deleted_comment)
        self.mock_db_session.add.assert_not_called()

if __name__ == '__main__':
    unittest.main()
