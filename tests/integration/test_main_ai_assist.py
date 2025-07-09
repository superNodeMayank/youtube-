import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session as SQLModelSession, select
from unittest.mock import patch

from src.models import User, Video, Comment, AICommentEdit
from tests.integration.conftest import create_test_user, get_auth_headers_for_user

# --- Test Data ---
AI_TEST_USER_USERNAME = "ai_user"
AI_TEST_USER_EMAIL = "ai_user@example.com"
AI_TEST_USER_PASSWORD = "ai_password"

# --- Fixtures ---
@pytest.fixture(scope="module")
def ai_test_user_auth_headers(client: TestClient, db_session: SQLModelSession):
    create_test_user(
        db_session,
        username=AI_TEST_USER_USERNAME,
        email=AI_TEST_USER_EMAIL,
        password=AI_TEST_USER_PASSWORD,
        ai_global_toggle=False # Start with AI assist globally off for some tests
    )
    return get_auth_headers_for_user(client, AI_TEST_USER_USERNAME, AI_TEST_USER_PASSWORD)

@pytest.fixture(scope="function")
def ai_test_video(client: TestClient, ai_test_user_auth_headers: dict, db_session: SQLModelSession) -> Video:
    user_in_db = db_session.exec(select(User).where(User.username == AI_TEST_USER_USERNAME)).first()
    assert user_in_db is not None

    video_data = {
        "title": "AI Test Video", "description": "Video for AI features.",
        "url": f"http://example.com/ai_video_{user_in_db.user_id}",
        "uploader_user_id": user_in_db.user_id
    }
    response = client.post("/videos/", json=video_data, headers=ai_test_user_auth_headers)
    response.raise_for_status()
    return Video(**response.json())

@pytest.fixture(scope="function")
def ai_test_comment(client: TestClient, ai_test_user_auth_headers: dict, ai_test_video: Video) -> Comment:
    comment_data = {"original_text": "This is a comment for AI testing.", "video_id": ai_test_video.video_id}
    response = client.post(
        f"/videos/{ai_test_video.video_id}/comments/",
        json=comment_data,
        headers=ai_test_user_auth_headers
    )
    response.raise_for_status()
    return Comment(**response.json())

# --- AI Assist Feature Tests ---

def test_update_user_ai_assist_global_toggle(client: TestClient, ai_test_user_auth_headers: dict, db_session: SQLModelSession):
    # 1. Check initial state (should be False from fixture setup)
    user_response = client.get("/users/me", headers=ai_test_user_auth_headers)
    user_response.raise_for_status()
    assert not user_response.json()["ai_assist_enabled_global"]

    # 2. Enable global AI assist
    settings_update = {"ai_assist_enabled_global": True}
    response = client.put("/users/me/settings", json=settings_update, headers=ai_test_user_auth_headers)
    assert response.status_code == 200, f"Failed to update settings: {response.text}"
    assert response.json()["ai_assist_enabled_global"] == True

    # Verify in DB (optional, but good for sanity)
    user_in_db = db_session.exec(select(User).where(User.username == AI_TEST_USER_USERNAME)).first()
    assert user_in_db.ai_assist_enabled_global == True

    # 3. Disable global AI assist
    settings_update = {"ai_assist_enabled_global": False}
    response = client.put("/users/me/settings", json=settings_update, headers=ai_test_user_auth_headers)
    assert response.status_code == 200
    assert response.json()["ai_assist_enabled_global"] == False


@patch('src.ai_services.enhance_comment_with_ai') # Mock the actual AI call
def test_enhance_comment_happy_path(mock_enhance_fn, client: TestClient, ai_test_user_auth_headers: dict, ai_test_comment: Comment, db_session: SQLModelSession):
    mock_enhance_fn.return_value = "This is the AI enhanced version of the comment."

    comment_id = ai_test_comment.comment_id
    response = client.post(f"/comments/{comment_id}/enhance", headers=ai_test_user_auth_headers)

    assert response.status_code == 200, f"Enhance failed: {response.text}"
    data = response.json()
    assert data["comment_id"] == comment_id
    assert data["original_text"] == ai_test_comment.original_text
    assert data["suggested_enhanced_text"] == "This is the AI enhanced version of the comment."
    assert data["status"] == "suggested"
    suggestion_id = data["suggestion_id"]

    # Verify AICommentEdit record was created
    ai_edit_record = db_session.get(AICommentEdit, suggestion_id)
    assert ai_edit_record is not None
    assert ai_edit_record.comment_id == comment_id
    assert ai_edit_record.raw_comment_text_before_ai == ai_test_comment.original_text
    assert ai_edit_record.ai_generated_text == "This is the AI enhanced version of the comment."
    assert ai_edit_record.status == "suggested"
    mock_enhance_fn.assert_called_once_with(ai_test_comment.original_text, user_prompt_template=None)


@patch('src.ai_services.enhance_comment_with_ai')
def test_enhance_comment_ai_service_failure(mock_enhance_fn, client: TestClient, ai_test_user_auth_headers: dict, ai_test_comment: Comment, db_session: SQLModelSession):
    mock_enhance_fn.return_value = None # Simulate AI failure or blocked content

    comment_id = ai_test_comment.comment_id
    response = client.post(f"/comments/{comment_id}/enhance", headers=ai_test_user_auth_headers)

    assert response.status_code == 503 # Service Unavailable
    assert "AI enhancement service failed or content was blocked" in response.json()["detail"]

    # Verify AICommentEdit record was created with 'api_error' status
    # Need to find the record as we don't get suggestion_id from a 503 response.
    # This requires querying.
    ai_edit_records = db_session.exec(
        select(AICommentEdit).where(AICommentEdit.comment_id == comment_id).order_by(AICommentEdit.api_call_timestamp.desc())
    ).all()
    assert len(ai_edit_records) > 0
    latest_ai_edit_record = ai_edit_records[0]
    assert latest_ai_edit_record.status == "api_error"
    assert latest_ai_edit_record.raw_comment_text_before_ai == ai_test_comment.original_text
    assert latest_ai_edit_record.ai_generated_text == "" # Stored as empty if None from AI

def test_enhance_comment_not_author(client: TestClient, ai_test_comment: Comment, db_session: SQLModelSession):
    # Create another user
    other_user_headers = get_auth_headers_for_user(
        client,
        create_test_user(db_session, username="otheraiuser", email="otherai@e.com", password="p").username,
        "p"
    )
    response = client.post(f"/comments/{ai_test_comment.comment_id}/enhance", headers=other_user_headers)
    assert response.status_code == 403 # Forbidden


# --- Review AI Suggestion Tests ---
@patch('src.ai_services.enhance_comment_with_ai')
def test_review_suggestion_accept_as_is(mock_enhance_fn, client: TestClient, ai_test_user_auth_headers: dict, ai_test_comment: Comment, db_session: SQLModelSession):
    ai_suggestion_text = "AI accepted version."
    mock_enhance_fn.return_value = ai_suggestion_text

    # 1. Get a suggestion
    enhance_resp = client.post(f"/comments/{ai_test_comment.comment_id}/enhance", headers=ai_test_user_auth_headers)
    enhance_resp.raise_for_status()
    suggestion_id = enhance_resp.json()["suggestion_id"]

    # 2. Review: Accept as is
    review_data = {"action": "accept_as_is"}
    review_resp = client.put(f"/ai-suggestions/{suggestion_id}/review", json=review_data, headers=ai_test_user_auth_headers)
    assert review_resp.status_code == 200, f"Review failed: {review_resp.text}"

    updated_comment_data = review_resp.json()
    assert updated_comment_data["comment_id"] == ai_test_comment.comment_id
    assert updated_comment_data["displayed_text"] == ai_suggestion_text
    assert updated_comment_data["is_ai_assisted"] == True
    assert updated_comment_data["original_text"] == ai_test_comment.original_text # Original is preserved

    # Verify AICommentEdit status
    ai_edit_record = db_session.get(AICommentEdit, suggestion_id)
    assert ai_edit_record.status == "accepted_as_is"


@patch('src.ai_services.enhance_comment_with_ai')
def test_review_suggestion_edit_and_accept(mock_enhance_fn, client: TestClient, ai_test_user_auth_headers: dict, ai_test_comment: Comment, db_session: SQLModelSession):
    mock_enhance_fn.return_value = "AI suggested this, but user will edit."
    enhance_resp = client.post(f"/comments/{ai_test_comment.comment_id}/enhance", headers=ai_test_user_auth_headers)
    enhance_resp.raise_for_status()
    suggestion_id = enhance_resp.json()["suggestion_id"]

    user_edited_text = "User's final edited version of AI suggestion."
    review_data = {"action": "edit_and_accept", "edited_text": user_edited_text}
    review_resp = client.put(f"/ai-suggestions/{suggestion_id}/review", json=review_data, headers=ai_test_user_auth_headers)
    assert review_resp.status_code == 200, f"Review (edit_and_accept) failed: {review_resp.text}"

    updated_comment_data = review_resp.json()
    assert updated_comment_data["displayed_text"] == user_edited_text
    assert updated_comment_data["is_ai_assisted"] == True

    ai_edit_record = db_session.get(AICommentEdit, suggestion_id)
    assert ai_edit_record.status == "edited_and_accepted"
    assert ai_edit_record.user_final_edited_text == user_edited_text


@patch('src.ai_services.enhance_comment_with_ai')
def test_review_suggestion_reject(mock_enhance_fn, client: TestClient, ai_test_user_auth_headers: dict, ai_test_comment: Comment, db_session: SQLModelSession):
    mock_enhance_fn.return_value = "A suggestion that will be rejected."
    enhance_resp = client.post(f"/comments/{ai_test_comment.comment_id}/enhance", headers=ai_test_user_auth_headers)
    enhance_resp.raise_for_status()
    suggestion_id = enhance_resp.json()["suggestion_id"]

    # First, accept a suggestion to make is_ai_assisted = True
    client.put(f"/ai-suggestions/{suggestion_id}/review", json={"action": "accept_as_is"}, headers=ai_test_user_auth_headers).raise_for_status()

    # Now, get another suggestion for the same comment
    mock_enhance_fn.return_value = "A newer suggestion to be rejected."
    enhance_resp_2 = client.post(f"/comments/{ai_test_comment.comment_id}/enhance", headers=ai_test_user_auth_headers)
    enhance_resp_2.raise_for_status()
    suggestion_id_2 = enhance_resp_2.json()["suggestion_id"]


    # Review: Reject the newer suggestion
    review_data = {"action": "reject"}
    review_resp = client.put(f"/ai-suggestions/{suggestion_id_2}/review", json=review_data, headers=ai_test_user_auth_headers)
    assert review_resp.status_code == 200, f"Review (reject) failed: {review_resp.text}"

    updated_comment_data = review_resp.json()
    # When rejected, displayed_text should revert to original_text if it was previously AI assisted
    assert updated_comment_data["displayed_text"] == ai_test_comment.original_text
    assert updated_comment_data["is_ai_assisted"] == False

    ai_edit_record = db_session.get(AICommentEdit, suggestion_id_2)
    assert ai_edit_record.status == "rejected"

    # Original comment should reflect the rejection
    final_comment_state = db_session.get(Comment, ai_test_comment.comment_id)
    assert final_comment_state.displayed_text == ai_test_comment.original_text
    assert final_comment_state.is_ai_assisted == False


def test_review_suggestion_already_actioned(mock_enhance_fn, client: TestClient, ai_test_user_auth_headers: dict, ai_test_comment: Comment):
    mock_enhance_fn.return_value = "Suggestion."
    enhance_resp = client.post(f"/comments/{ai_test_comment.comment_id}/enhance", headers=ai_test_user_auth_headers)
    enhance_resp.raise_for_status()
    suggestion_id = enhance_resp.json()["suggestion_id"]

    # Action it once
    client.put(f"/ai-suggestions/{suggestion_id}/review", json={"action": "accept_as_is"}, headers=ai_test_user_auth_headers).raise_for_status()

    # Try to action it again
    review_data = {"action": "reject"}
    review_resp_again = client.put(f"/ai-suggestions/{suggestion_id}/review", json=review_data, headers=ai_test_user_auth_headers)
    assert review_resp_again.status_code == 400 # Bad Request
    assert "already been actioned" in review_resp_again.json()["detail"]

# Add tests for edge input content (empty comment, long comment, special chars) for /enhance endpoint
# Add tests for global opt-out (user has ai_assist_enabled_global=False, tries /enhance)
# - This requires setting user's global toggle, then attempting enhance.
# - The current /enhance endpoint doesn't check global toggle, it's an explicit action.
# - If global toggle OFF should prevent /enhance, that logic needs to be added to the endpoint.
# - For now, global toggle is for client-side hints or potential auto-suggestions (not implemented).

# Test for enhancing a comment that was previously AI-assisted and then manually edited
# - Create comment -> Enhance -> Accept -> Update comment manually -> Enhance again
# - Ensure the `raw_comment_text_before_ai` in the new AICommentEdit record is the manually updated text.
# - This is implicitly handled if `enhance` uses `db_comment.original_text`. If it should use `db_comment.displayed_text`, that's a change.
# - Current `enhance` uses `db_comment.original_text`. This is simpler and always enhances the pure original.
# - If requirement is to enhance the *current displayed text*, then `enhance` endpoint needs to use `db_comment.displayed_text`.
# - The requirement "each user’s raw comment is converted into a prompt" suggests using original_text is correct.

# Test for AI fallback if AI returns empty/whitespace (covered by mocking enhance_comment_with_ai to return None/empty)
# - This is tested in test_enhance_comment_ai_service_failure.

# Test for permissions (already have test_enhance_comment_not_author, test_review_suggestion_not_author (implicitly via comment ownership))

# Test for long comment / special chars
@patch('src.ai_services.enhance_comment_with_ai')
def test_enhance_comment_long_text_and_special_chars(mock_enhance_fn, client: TestClient, ai_test_user_auth_headers: dict, ai_test_video: Video, db_session: SQLModelSession):
    long_text = "a" * 1000 + " !@#$%^&*()_+{}\":?><|"
    comment_data = {"original_text": long_text, "video_id": ai_test_video.video_id}
    create_resp = client.post(f"/videos/{ai_test_video.video_id}/comments/", json=comment_data, headers=ai_test_user_auth_headers)
    create_resp.raise_for_status()
    comment_id = create_resp.json()["comment_id"]

    mock_enhance_fn.return_value = "Enhanced long text with specials."

    response = client.post(f"/comments/{comment_id}/enhance", headers=ai_test_user_auth_headers)
    assert response.status_code == 200
    assert response.json()["suggested_enhanced_text"] == "Enhanced long text with specials."
    mock_enhance_fn.assert_called_once_with(long_text, user_prompt_template=None)
