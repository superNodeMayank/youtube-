import unittest
from unittest.mock import MagicMock, patch

from src import crud
from src.models import User
from src.schemas import UserCreate
from src.auth import get_password_hash # Used by crud.create_user

class TestCrudUsers(unittest.TestCase):

    def test_get_user(self):
        mock_db_session = MagicMock()
        user_id = 1
        expected_user = User(user_id=user_id, username="testuser", email="test@example.com", password_hash="hashed")

        mock_db_session.get.return_value = expected_user

        user = crud.get_user(mock_db_session, user_id)

        self.assertEqual(user, expected_user)
        mock_db_session.get.assert_called_once_with(User, user_id)

    def test_get_user_not_found(self):
        mock_db_session = MagicMock()
        user_id = 99
        mock_db_session.get.return_value = None

        user = crud.get_user(mock_db_session, user_id)

        self.assertIsNone(user)
        mock_db_session.get.assert_called_once_with(User, user_id)

    def test_get_user_by_username(self):
        mock_db_session = MagicMock()
        username = "testuser"
        expected_user = User(user_id=1, username=username, email="test@example.com", password_hash="hashed")

        # Mock the chain: session.exec().first()
        mock_exec_result = MagicMock()
        mock_exec_result.first.return_value = expected_user
        mock_db_session.exec.return_value = mock_exec_result

        user = crud.get_user_by_username(mock_db_session, username)

        self.assertEqual(user, expected_user)
        mock_db_session.exec.assert_called_once()
        # We could also assert the select statement if we capture it, but it's more involved.

    def test_get_user_by_email(self):
        mock_db_session = MagicMock()
        email = "test@example.com"
        expected_user = User(user_id=1, username="testuser", email=email, password_hash="hashed")

        mock_exec_result = MagicMock()
        mock_exec_result.first.return_value = expected_user
        mock_db_session.exec.return_value = mock_exec_result

        user = crud.get_user_by_email(mock_db_session, email)

        self.assertEqual(user, expected_user)
        mock_db_session.exec.assert_called_once()

    @patch('src.crud.get_password_hash') # Mock get_password_hash used within create_user
    def test_create_user(self, mock_get_password_hash):
        mock_db_session = MagicMock()

        user_data = UserCreate(
            username="newuser",
            email="new@example.com",
            password="newpassword",
            ai_assist_enabled_global=True
        )

        expected_hashed_password = "hashed_new_password"
        mock_get_password_hash.return_value = expected_hashed_password

        # The actual User object that would be created and returned after db.refresh()
        # For simplicity, we'll assume db.refresh updates the passed object or a similar one.

        created_user = crud.create_user(mock_db_session, user_data)

        mock_get_password_hash.assert_called_once_with(user_data.password)

        # Assert that a User instance was added to the session
        # This requires inspecting the arguments to db.add()
        args, _ = mock_db_session.add.call_args
        added_user_instance = args[0]

        self.assertIsInstance(added_user_instance, User)
        self.assertEqual(added_user_instance.username, user_data.username)
        self.assertEqual(added_user_instance.email, user_data.email)
        self.assertEqual(added_user_instance.password_hash, expected_hashed_password)
        self.assertEqual(added_user_instance.ai_assist_enabled_global, user_data.ai_assist_enabled_global)

        mock_db_session.add.assert_called_once_with(added_user_instance)
        mock_db_session.commit.assert_called_once()
        mock_db_session.refresh.assert_called_once_with(added_user_instance)

        # The returned user should be the one that was refreshed
        self.assertEqual(created_user, added_user_instance)


    def test_update_user_settings(self):
        mock_db_session = MagicMock()
        user_id = 1
        existing_user = User(user_id=user_id, username="testuser", email="test@example.com", password_hash="hashed", ai_assist_enabled_global=False)

        # Mock get_user call within update_user_settings
        with patch('src.crud.get_user', return_value=existing_user) as mock_internal_get_user:
            settings_update_data = schemas.UserSettingsUpdate(ai_assist_enabled_global=True)

            updated_user = crud.update_user_settings(mock_db_session, user_id, settings_update_data)

            mock_internal_get_user.assert_called_once_with(mock_db_session, user_id)
            self.assertTrue(updated_user.ai_assist_enabled_global)

            mock_db_session.add.assert_called_once_with(existing_user) # or updated_user, should be same obj
            mock_db_session.commit.assert_called_once()
            mock_db_session.refresh.assert_called_once_with(existing_user)
            self.assertEqual(updated_user, existing_user)

    def test_update_user_settings_no_change(self):
        mock_db_session = MagicMock()
        user_id = 1
        existing_user = User(user_id=user_id, username="testuser", email="test@example.com", password_hash="hashed", ai_assist_enabled_global=False)

        with patch('src.crud.get_user', return_value=existing_user):
            # Update with None or same value should not trigger DB commit
            settings_update_data = schemas.UserSettingsUpdate(ai_assist_enabled_global=None)
            crud.update_user_settings(mock_db_session, user_id, settings_update_data)
            mock_db_session.commit.assert_not_called()

            settings_update_data_same = schemas.UserSettingsUpdate(ai_assist_enabled_global=False)
            crud.update_user_settings(mock_db_session, user_id, settings_update_data_same)
            # This will still set updated=True because the field is provided, even if value is same.
            # The logic in crud.py is `if settings_data.field is not None: user.field = data; updated = True`
            # To avoid commit if value is same, crud.py would need: `if data is not None and user.field != data: ...`
            # For now, testing current behavior: it will commit if field is provided in UserSettingsUpdate.
            self.assertEqual(mock_db_session.commit.call_count, 1) # From the settings_update_data_same call

    def test_update_user_settings_user_not_found(self):
        mock_db_session = MagicMock()
        user_id = 99
        with patch('src.crud.get_user', return_value=None):
            settings_update_data = schemas.UserSettingsUpdate(ai_assist_enabled_global=True)
            updated_user = crud.update_user_settings(mock_db_session, user_id, settings_update_data)
            self.assertIsNone(updated_user)
            mock_db_session.commit.assert_not_called()

if __name__ == '__main__':
    # Need to import schemas for UserSettingsUpdate
    from src import schemas
    unittest.main()
