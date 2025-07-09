import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session as SQLModelSession

from src.models import User, Video # For type hinting and direct DB interaction if needed
from tests.integration.conftest import create_test_user, get_auth_headers_for_user

# --- Test Data ---
TEST_USER_USERNAME = "comment_user"
TEST_USER_EMAIL = "comment_user@example.com"
TEST_USER_PASSWORD = "comment_password"

# --- Fixtures specific to this test file (if any) ---
@pytest.fixture(scope="module") # Create one user for all tests in this module
def test_user_auth_headers(client: TestClient, db_session: SQLModelSession):
    # Create the user directly in DB for this module
    create_test_user(
        db_session,
        username=TEST_USER_USERNAME,
        email=TEST_USER_EMAIL,
        password=TEST_USER_PASSWORD
    )
    # Login and get headers
    return get_auth_headers_for_user(client, TEST_USER_USERNAME, TEST_USER_PASSWORD)

@pytest.fixture(scope="function") # Create a new video for each test function that needs one
def test_video(client: TestClient, test_user_auth_headers: dict, db_session: SQLModelSession) -> Video:
    # Get current user ID from token to correctly set uploader_user_id
    # (Alternatively, if test_user_auth_headers could return user_id, that'd be cleaner)
    # For simplicity, assume user ID 1 if it's the first user created, or fetch it.

    # Fetch the user_id for TEST_USER_USERNAME
    user_in_db = db_session.query(User).filter(User.username == TEST_USER_USERNAME).first()
    assert user_in_db is not None, "Test user not found in DB for video creation"

    video_data = {
        "title": "Test Video for Comments",
        "description": "A video to test comment functionality.",
        "url": f"http://example.com/test_video_{user_in_db.user_id}_{db_session.get_bind().dialect.name}", # Unique URL
        "uploader_user_id": user_in_db.user_id
    }
    response = client.post("/videos/", json=video_data, headers=test_user_auth_headers)
    assert response.status_code == 201, f"Failed to create video: {response.text}"
    return Video(**response.json()) # Create a Video model instance from response


# --- Commenting Tests ---

def test_create_comment_on_video(client: TestClient, test_user_auth_headers: dict, test_video: Video):
    comment_data = {
        "original_text": "This is a great video!",
        "video_id": test_video.video_id
        # parent_comment_id is optional
    }
    response = client.post(
        f"/videos/{test_video.video_id}/comments/",
        json=comment_data,
        headers=test_user_auth_headers
    )
    assert response.status_code == 201, f"Failed to create comment: {response.text}"
    data = response.json()
    assert data["original_text"] == comment_data["original_text"]
    assert data["displayed_text"] == comment_data["original_text"] # Initially same
    assert not data["is_ai_assisted"]
    assert data["video_id"] == test_video.video_id
    assert data["author"]["username"] == TEST_USER_USERNAME

def test_create_comment_video_not_found(client: TestClient, test_user_auth_headers: dict):
    non_existent_video_id = 99999
    comment_data = {"original_text": "Comment on non-existent video", "video_id": non_existent_video_id}
    response = client.post(
        f"/videos/{non_existent_video_id}/comments/",
        json=comment_data,
        headers=test_user_auth_headers
    )
    assert response.status_code == 404 # Video not found by CRUD check
    assert "Video with id 99999 not found" in response.json()["detail"]


def test_get_comments_for_video(client: TestClient, test_user_auth_headers: dict, test_video: Video):
    # Create a couple of comments first
    client.post(f"/videos/{test_video.video_id}/comments/", json={"original_text": "First comment!", "video_id": test_video.video_id}, headers=test_user_auth_headers).raise_for_status()
    client.post(f"/videos/{test_video.video_id}/comments/", json={"original_text": "Second comment!", "video_id": test_video.video_id}, headers=test_user_auth_headers).raise_for_status()

    response = client.get(f"/videos/{test_video.video_id}/comments/")
    assert response.status_code == 200
    comments = response.json()
    assert len(comments) == 2
    assert comments[0]["original_text"] == "Second comment!" # Default order is newest first (desc by created_at)
    assert comments[1]["original_text"] == "First comment!"


def test_get_single_comment(client: TestClient, test_user_auth_headers: dict, test_video: Video):
    create_response = client.post(f"/videos/{test_video.video_id}/comments/", json={"original_text": "A specific comment", "video_id": test_video.video_id}, headers=test_user_auth_headers)
    create_response.raise_for_status()
    comment_id = create_response.json()["comment_id"]

    response = client.get(f"/comments/{comment_id}")
    assert response.status_code == 200
    comment = response.json()
    assert comment["comment_id"] == comment_id
    assert comment["original_text"] == "A specific comment"


def test_update_comment(client: TestClient, test_user_auth_headers: dict, test_video: Video):
    create_response = client.post(f"/videos/{test_video.video_id}/comments/", json={"original_text": "Original text for update", "video_id": test_video.video_id}, headers=test_user_auth_headers)
    create_response.raise_for_status()
    comment_id = create_response.json()["comment_id"]

    update_data = {"original_text": "Updated text for the comment"} # CommentBase schema for update
    response = client.put(f"/comments/{comment_id}", json=update_data, headers=test_user_auth_headers)
    assert response.status_code == 200, f"Failed to update comment: {response.text}"
    updated_comment = response.json()
    assert updated_comment["comment_id"] == comment_id
    assert updated_comment["displayed_text"] == update_data["original_text"]
    assert updated_comment["original_text"] == "Original text for update" # Original text remains unchanged

def test_update_comment_not_author(client: TestClient, test_user_auth_headers: dict, test_video: Video, db_session: SQLModelSession):
    # Create comment with test_user
    create_response = client.post(f"/videos/{test_video.video_id}/comments/", json={"original_text": "Author's comment", "video_id": test_video.video_id}, headers=test_user_auth_headers)
    create_response.raise_for_status()
    comment_id = create_response.json()["comment_id"]

    # Create another user and try to update
    other_user_username = "other_user_comment"
    other_user_password = "other_password"
    create_test_user(db_session, username=other_user_username, email="other_comment@example.com", password=other_user_password)
    other_user_headers = get_auth_headers_for_user(client, other_user_username, other_user_password)

    update_data = {"original_text": "Attempted update by other user"}
    response = client.put(f"/comments/{comment_id}", json=update_data, headers=other_user_headers)
    assert response.status_code == 403 # Forbidden
    assert "Not authorized to update this comment" in response.json()["detail"]


def test_delete_comment(client: TestClient, test_user_auth_headers: dict, test_video: Video):
    create_response = client.post(f"/videos/{test_video.video_id}/comments/", json={"original_text": "Comment to be deleted", "video_id": test_video.video_id}, headers=test_user_auth_headers)
    create_response.raise_for_status()
    comment_id = create_response.json()["comment_id"]

    response = client.delete(f"/comments/{comment_id}", headers=test_user_auth_headers)
    assert response.status_code == 200, f"Failed to delete comment: {response.text}"
    assert response.json()["message"] == "Comment deleted successfully"

    # Verify comment is marked as deleted (or returns 404)
    get_response = client.get(f"/comments/{comment_id}")
    assert get_response.status_code == 404 # Soft delete makes it not found for regular GET
    # Or, if it returns the comment with is_deleted=True and masked text:
    # assert get_response.json()["is_deleted"] == True
    # assert get_response.json()["displayed_text"] == "This comment has been deleted."


def test_delete_comment_not_author(client: TestClient, test_user_auth_headers: dict, test_video: Video, db_session: SQLModelSession):
    create_response = client.post(f"/videos/{test_video.video_id}/comments/", json={"original_text": "Another author's comment", "video_id": test_video.video_id}, headers=test_user_auth_headers)
    create_response.raise_for_status()
    comment_id = create_response.json()["comment_id"]

    other_user_username = "deleter_user"
    other_user_password = "deleter_password"
    create_test_user(db_session, username=other_user_username, email="deleter@example.com", password=other_user_password)
    other_user_headers = get_auth_headers_for_user(client, other_user_username, other_user_password)

    response = client.delete(f"/comments/{comment_id}", headers=other_user_headers)
    assert response.status_code == 403
    assert "Not authorized to delete this comment" in response.json()["detail"]

# TODO: Add tests for threaded comments (replies) if time permits / as per priority.
# - Create a comment, then create a reply to it.
# - Verify get_comments_for_video includes replies nested correctly.
# - Verify get_comment_replies (if a direct endpoint exists, or check via parent comment).
