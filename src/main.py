from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session # Changed from sqlmodel Session for type hinting with FastAPI Depends
from typing import List, Annotated

from src import crud, models, schemas, auth
from src.database import engine, get_session, create_db_and_tables
from src.config import settings

# Create database tables if they don't exist
# This should be called once when the application starts.
# models.SQLModel.metadata.create_all(bind=engine) # Alternative way if models are imported
# For our setup, create_db_and_tables() in database.py handles imports and creation.
create_db_and_tables()


app = FastAPI(title="YouTube Comment AI Enhancement API")

# --- Authentication Dependencies ---
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token") # Endpoint for users to get a token

async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[Session, Depends(get_session)]
) -> models.User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    token_data = auth.verify_token(token, credentials_exception)
    user = crud.get_user_by_username(db, username=token_data.username)
    if user is None:
        raise credentials_exception
    return user

async def get_current_active_user(
    current_user: Annotated[models.User, Depends(get_current_user)]
):
    # Add logic here if users can be deactivated
    # if current_user.disabled:
    #     raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

# Type alias for dependency injection
DBSession = Annotated[Session, Depends(get_session)]
CurrentUser = Annotated[models.User, Depends(get_current_active_user)]


# --- API Endpoints ---

# Authentication
@app.post("/token", response_model=schemas.Token)
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: DBSession
):
    user = crud.get_user_by_username(db, username=form_data.username)
    if not user or not auth.verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = auth.create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/users/register", response_model=schemas.UserRead, status_code=status.HTTP_201_CREATED)
def register_user(user: schemas.UserRegister, db: DBSession):
    db_user_by_username = crud.get_user_by_username(db, username=user.username)
    if db_user_by_username:
        raise HTTPException(status_code=400, detail="Username already registered")
    db_user_by_email = crud.get_user_by_email(db, email=user.email)
    if db_user_by_email:
        raise HTTPException(status_code=400, detail="Email already registered")
    return crud.create_user(db=db, user=user)

@app.get("/users/me", response_model=schemas.UserRead)
async def read_users_me(current_user: CurrentUser):
    return current_user

@app.put("/users/me/settings", response_model=schemas.UserRead)
async def update_user_settings_endpoint(
    settings_data: schemas.UserSettingsUpdate,
    current_user: CurrentUser,
    db: DBSession
):
    updated_user = crud.update_user_settings(db, user_id=current_user.user_id, settings_data=settings_data)
    if not updated_user:
        # This should ideally not happen if current_user is valid, but as a safeguard
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return schemas.UserRead.model_validate(updated_user)


# Videos (Simplified for comment context)
@app.post("/videos/", response_model=schemas.VideoRead, status_code=status.HTTP_201_CREATED)
def create_video_endpoint(video: schemas.VideoCreate, db: DBSession, current_user: CurrentUser):
    # Basic check: ensure uploader is the current user or admin (not implemented)
    if video.uploader_user_id != current_user.user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to create video for this user")
    return crud.create_video(db=db, video=video)

@app.get("/videos/", response_model=List[schemas.VideoRead])
def read_videos_endpoint(skip: int = 0, limit: int = 10, db: DBSession):
    videos = crud.get_videos(db, skip=skip, limit=limit)
    return videos

@app.get("/videos/{video_id}", response_model=schemas.VideoRead)
def read_video_endpoint(video_id: int, db: DBSession):
    db_video = crud.get_video(db, video_id=video_id)
    if db_video is None:
        raise HTTPException(status_code=404, detail="Video not found")
    return db_video


# Comments
@app.post("/videos/{video_id}/comments/", response_model=schemas.CommentReadAPI, status_code=status.HTTP_201_CREATED)
def create_comment_endpoint(
    video_id: int, # Path parameter
    comment_data: schemas.CommentCreateAPI, # Request body
    db: DBSession,
    current_user: CurrentUser
):
    if comment_data.video_id != video_id:
        raise HTTPException(status_code=400, detail="Video ID in path and body do not match.")
    try:
        return crud.create_comment(db=db, comment_data=comment_data, user_id=current_user.user_id)
    except ValueError as e: # Catch errors from CRUD, e.g., video not found
        raise HTTPException(status_code=404, detail=str(e))


def get_comment_with_replies_recursively(db_comment: models.Comment, db: Session) -> schemas.CommentReadAPI:
    """ Helper to fetch a comment and its replies, recursively for the schema. """
    replies_models = crud.get_comment_replies(db, parent_comment_id=db_comment.comment_id, limit=100) # Adjust limit as needed

    # Convert model replies to schema replies, recursively
    schema_replies = [get_comment_with_replies_recursively(reply, db) for reply in replies_models]

    # Create the CommentReadAPI object for the current comment
    comment_api_data = schemas.CommentReadAPI.model_validate(db_comment)
    comment_api_data.replies = schema_replies

    return comment_api_data


@app.get("/videos/{video_id}/comments/", response_model=List[schemas.CommentReadAPI])
def read_comments_for_video_endpoint(video_id: int, skip: int = 0, limit: int = 10, db: DBSession):
    # Ensure video exists
    db_video = crud.get_video(db, video_id=video_id)
    if not db_video:
        raise HTTPException(status_code=404, detail=f"Video with id {video_id} not found.")

    comments_models = crud.get_comments_for_video(db, video_id=video_id, skip=skip, limit=limit)

    # For each top-level comment, fetch its replies
    comments_api_list = []
    for comment_model in comments_models:
        comments_api_list.append(get_comment_with_replies_recursively(comment_model, db))

    return comments_api_list


@app.get("/comments/{comment_id}", response_model=schemas.CommentReadAPI)
def read_comment_endpoint(comment_id: int, db: DBSession):
    db_comment = crud.get_comment(db, comment_id=comment_id)
    if db_comment is None or db_comment.is_deleted:
        raise HTTPException(status_code=404, detail="Comment not found")
    return get_comment_with_replies_recursively(db_comment, db)


@app.put("/comments/{comment_id}", response_model=schemas.CommentReadAPI)
def update_comment_endpoint(
    comment_id: int,
    comment_update: schemas.CommentBase, # User can only update text fields from CommentBase
    db: DBSession,
    current_user: CurrentUser
):
    updated_comment = crud.update_comment_text(
        db=db,
        comment_id=comment_id,
        new_text=comment_update.original_text, # Assuming user sends new text in 'original_text' field of CommentBase
        user_id=current_user.user_id
    )
    if updated_comment is None:
        # Could be comment not found, or user not authorized, or comment deleted
        # Check the original comment to give a more specific error
        original_comment = crud.get_comment(db, comment_id)
        if not original_comment or original_comment.is_deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comment not found or has been deleted.")
        if original_comment.user_id != current_user.user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to update this comment.")
        # If it reached here, something else went wrong, though crud.update_comment_text should handle it.
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not update comment.")

    return get_comment_with_replies_recursively(updated_comment, db)


@app.delete("/comments/{comment_id}", response_model=schemas.Message)
def delete_comment_endpoint(comment_id: int, db: DBSession, current_user: CurrentUser):
    deleted_comment = crud.delete_comment(db=db, comment_id=comment_id, user_id=current_user.user_id)
    if deleted_comment is None:
        # Similar logic to update to determine the cause
        original_comment = crud.get_comment(db, comment_id)
        if not original_comment or original_comment.is_deleted : # if already deleted by this point, still treat as success or 404
             raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comment not found or already deleted.")
        if original_comment.user_id != current_user.user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to delete this comment.")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not delete comment.")
    return {"message": "Comment deleted successfully"}


# Health check endpoint
@app.get("/health")
async def health_check():
    # Optionally, check DB connection too
    try:
        # Ensure correct Session type for execute
        with engine.connect() as connection:
            connection.execute(models.text("SELECT 1")) # Use models.text for raw SQL with SQLAlchemy engine
            connection.commit() # Not strictly necessary for SELECT 1, but good practice for other test queries
        return {"status": "ok", "database": "connected"}
    except Exception as e:
        # Log the exception e for debugging
        return {"status": "ok", "database": "error", "detail": str(e)}


# --- AI Enhancement Endpoints ---

@app.post("/comments/{comment_id}/enhance", response_model=schemas.EnhanceCommentResponse)
async def enhance_comment_endpoint(
    comment_id: int,
    request_body: schemas.EnhanceCommentRequest = None, # Optional body for custom prompt
    db: DBSession = Depends(get_session),
    current_user: CurrentUser = Depends(get_current_active_user)
):
    from src import ai_services # Local import to avoid circular dependency issues at startup

    db_comment = crud.get_comment(db, comment_id=comment_id)

    if not db_comment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comment not found")
    if db_comment.is_deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comment has been deleted")
    if db_comment.user_id != current_user.user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to enhance this comment")

    text_to_enhance = db_comment.original_text
    prompt_template_to_use = request_body.prompt_template if request_body else None

    enhanced_text = ai_services.enhance_comment_with_ai(
        text_to_enhance,
        user_prompt_template=prompt_template_to_use
    )

    enhancement_log_status = "suggested"
    error_message_for_db = None

    if enhanced_text is None:
        enhancement_log_status = "api_error"
        error_message_for_db = "AI service failed or content was blocked."

    actual_prompt_logged = ""
    if prompt_template_to_use:
        actual_prompt_logged = prompt_template_to_use.format(comment=text_to_enhance)
    else:
        actual_prompt_logged = f"Default prompt for: \"{text_to_enhance[:100]}...\""

    log_db_input = schemas.AIEnhancementLogDBInput(
        comment_id=comment_id,
        user_id=current_user.user_id,
        raw_comment_text_before_ai=text_to_enhance,
        ai_prompt_used=actual_prompt_logged,
        ai_generated_text=enhanced_text if enhanced_text else "",
        status=enhancement_log_status,
        ai_model_used=ai_services.MODEL_NAME,
        api_error_message=error_message_for_db if enhancement_log_status != "suggested" else None
    )

    try:
        created_log_entry = crud.create_ai_enhancement_log(db, log_db_input)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    if enhancement_log_status != "suggested":
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=error_message_for_db)

    return schemas.EnhanceCommentResponse(
        suggestion_id=created_log_entry.log_id, # Use log_id
        comment_id=comment_id,
        original_text=text_to_enhance,
        suggested_enhanced_text=enhanced_text,
        status=created_log_entry.status
    )

@app.put("/ai-enhancement-logs/{log_id}/review", response_model=schemas.CommentReadAPI) # Path updated
async def review_ai_enhancement_endpoint(
    log_id: int, # Changed from suggestion_id to log_id
    review_data: schemas.ReviewEnhancementRequest,
    db: DBSession = Depends(get_session),
    current_user: CurrentUser = Depends(get_current_active_user)
):
    enhancement_log_record = crud.get_ai_enhancement_log(db, log_id=log_id)

    if not enhancement_log_record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="AI enhancement log not found.")

    db_comment = crud.get_comment(db, comment_id=enhancement_log_record.comment_id)
    if not db_comment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Associated comment not found.")
    if db_comment.is_deleted:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot review suggestion for a deleted comment.")

    if db_comment.user_id != current_user.user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to review this AI suggestion.")

    if enhancement_log_record.status != "suggested":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"This AI suggestion (log ID: {log_id}) has already been actioned with status: {enhancement_log_record.status}.")

    new_status = ""
    user_final_text_for_log = None
    text_to_validate = ""

    if review_data.action == "accept_as_is":
        text_to_validate = enhancement_log_record.ai_generated_text
        if len(text_to_validate) > settings.MAX_COMMENT_LENGTH:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"AI generated text exceeds maximum comment length of {settings.MAX_COMMENT_LENGTH} characters."
            )
        db_comment.displayed_text = text_to_validate
        db_comment.is_ai_assisted = True
        new_status = "accepted_as_is"

    elif review_data.action == "edit_and_accept":
        if not review_data.edited_text or not review_data.edited_text.strip():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Edited text cannot be empty for 'edit_and_accept' action.")

        text_to_validate = review_data.edited_text
        if len(text_to_validate) > settings.MAX_COMMENT_LENGTH:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Your edited text exceeds maximum comment length of {settings.MAX_COMMENT_LENGTH} characters."
            )
        db_comment.displayed_text = text_to_validate
        db_comment.is_ai_assisted = True
        new_status = "edited_and_accepted"
        user_final_text_for_log = review_data.edited_text

    elif review_data.action == "reject":
        if db_comment.is_ai_assisted:
            db_comment.displayed_text = db_comment.original_text
            db_comment.is_ai_assisted = False
        new_status = "rejected"

    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid review action.")

    db.add(db_comment)

    updated_log_entry = crud.update_ai_enhancement_log_status(
        db,
        log_id=log_id,
        status=new_status,
        user_final_text=user_final_text_for_log
    )
    if not updated_log_entry:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update AI enhancement log status.")

    db.commit()
    db.refresh(db_comment)

    return get_comment_api_representation(db_comment, db)


# To run the app (from project root):
# uvicorn src.main:app --reload --port 8000
# Ensure .env file is in the root directory or src/ directory based on load_dotenv() path.
# For this setup, .env should be in the root with src/.env.example as a template.
# The load_dotenv() in config.py might need adjustment if .env is not found.
# (It's currently loading from the current working directory of the script, which is fine if run via uvicorn src.main:app from root)

# Note: The get_comment_with_replies_recursively can lead to N+1 query problem if not careful,
# especially with many levels of replies. For a production system, consider optimizing
# reply fetching (e.g., common table expressions (CTEs) if the DB supports it, or limiting depth).
# For now, it demonstrates the structure.
