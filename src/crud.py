from sqlmodel import Session, select
from typing import List, Optional

from src import models
from src import schemas
from src.auth import get_password_hash

# --- User CRUD ---
def get_user(db: Session, user_id: int) -> Optional[models.User]:
    return db.get(models.User, user_id)

def get_user_by_username(db: Session, username: str) -> Optional[models.User]:
    statement = select(models.User).where(models.User.username == username)
    return db.exec(statement).first()

def get_user_by_email(db: Session, email: str) -> Optional[models.User]:
    statement = select(models.User).where(models.User.email == email)
    return db.exec(statement).first()

def create_user(db: Session, user: schemas.UserCreate) -> models.User:
    hashed_password = get_password_hash(user.password)
    db_user = models.User(
        username=user.username,
        email=user.email,
        password_hash=hashed_password,
        ai_assist_enabled_global=user.ai_assist_enabled_global
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def update_user_settings(db: Session, user_id: int, settings_data: schemas.UserSettingsUpdate) -> Optional[models.User]:
    db_user = get_user(db, user_id)
    if not db_user:
        return None

    updated = False
    if settings_data.ai_assist_enabled_global is not None:
        db_user.ai_assist_enabled_global = settings_data.ai_assist_enabled_global
        updated = True

    # Add other settings here if any
    # if settings_data.another_setting is not None:
    #     db_user.another_setting = settings_data.another_setting
    #     updated = True

    if updated:
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
    return db_user

# --- Video CRUD (Basic) ---
def get_video(db: Session, video_id: int) -> Optional[models.Video]:
    return db.get(models.Video, video_id)

def create_video(db: Session, video: schemas.VideoCreate) -> models.Video:
    # In a real app, ensure uploader_user_id exists or handle error
    db_video = models.Video.model_validate(video) # SQLModel way
    db.add(db_video)
    db.commit()
    db.refresh(db_video)
    return db_video

def get_videos(db: Session, skip: int = 0, limit: int = 100) -> List[models.Video]:
    statement = select(models.Video).offset(skip).limit(limit)
    return db.exec(statement).all()


# --- Comment CRUD ---
def create_comment(db: Session, comment_data: schemas.CommentCreateAPI, user_id: int) -> models.Comment:
    # Ensure video exists
    db_video = get_video(db, comment_data.video_id)
    if not db_video:
        raise ValueError(f"Video with id {comment_data.video_id} not found.")

    # Ensure parent comment exists if parent_comment_id is provided
    if comment_data.parent_comment_id:
        parent_comment = get_comment(db, comment_data.parent_comment_id)
        if not parent_comment:
            raise ValueError(f"Parent comment with id {comment_data.parent_comment_id} not found.")
        if parent_comment.video_id != comment_data.video_id:
             raise ValueError("Parent comment does not belong to the same video.")


    db_comment = models.Comment(
        original_text=comment_data.original_text,
        displayed_text=comment_data.original_text, # Initially same as original
        is_ai_assisted=False, # Default for new comments
        video_id=comment_data.video_id,
        user_id=user_id,
        parent_comment_id=comment_data.parent_comment_id,
        # ai_enhancement_enabled_per_comment will be its default (None)
    )
    db.add(db_comment)
    db.commit()
    db.refresh(db_comment)
    return db_comment

def get_comment(db: Session, comment_id: int) -> Optional[models.Comment]:
    return db.get(models.Comment, comment_id)

def get_comments_for_video(db: Session, video_id: int, skip: int = 0, limit: int = 100) -> List[models.Comment]:
    # Fetch only top-level comments for now (can be expanded for threads)
    statement = (
        select(models.Comment)
        .where(models.Comment.video_id == video_id)
        .where(models.Comment.parent_comment_id == None) # Top-level comments
        .where(models.Comment.is_deleted == False)
        .offset(skip)
        .limit(limit)
        .order_by(models.Comment.created_at.desc()) # Or asc, depending on desired order
    )
    return db.exec(statement).all()

def get_comment_replies(db: Session, parent_comment_id: int, skip: int = 0, limit: int = 100) -> List[models.Comment]:
    statement = (
        select(models.Comment)
        .where(models.Comment.parent_comment_id == parent_comment_id)
        .where(models.Comment.is_deleted == False)
        .offset(skip)
        .limit(limit)
        .order_by(models.Comment.created_at.asc()) # Replies usually in ascending order
    )
    return db.exec(statement).all()


def update_comment_text(db: Session, comment_id: int, new_text: str, user_id: int) -> Optional[models.Comment]:
    """
    Updates the displayed_text of a comment.
    Only the author should be able to update their comment.
    This will be used for regular edits. AI edits will have a more complex flow.
    """
    db_comment = db.get(models.Comment, comment_id)
    if db_comment and db_comment.user_id == user_id and not db_comment.is_deleted:
        db_comment.displayed_text = new_text
        # original_text remains unchanged
        # If this edit is manual after an AI suggestion, is_ai_assisted might need adjustment
        # For now, this is a simple text update.
        db.add(db_comment)
        db.commit()
        db.refresh(db_comment)
        return db_comment
    return None

# --- AICommentEdit CRUD ---

def create_ai_comment_edit(db: Session, ai_edit_data: schemas.AICommentEditDBInput) -> models.AICommentEdit:
    """
    Creates a record of an AI enhancement attempt/result.
    """
    # Ensure the associated comment exists
    comment = get_comment(db, ai_edit_data.comment_id)
    if not comment:
        raise ValueError(f"Comment with id {ai_edit_data.comment_id} not found for AI edit record.")

    # Ensure the user_id in ai_edit_data matches the comment's author,
    # or handle based on specific logic (e.g., if a moderator can trigger AI edit).
    # For now, assume user_id in AICommentEditDBInput is the comment author.
    if comment.user_id != ai_edit_data.user_id:
        # This might be a strict check; adjust if other users can initiate AI edits for a comment.
        raise ValueError(f"User ID {ai_edit_data.user_id} does not match comment author ID {comment.user_id}.")

    db_ai_edit = models.AICommentEdit.model_validate(ai_edit_data)
    db.add(db_ai_edit)
    db.commit()
    db.refresh(db_ai_edit)
    return db_ai_edit

def get_ai_comment_edit(db: Session, edit_id: int) -> Optional[models.AICommentEdit]:
    return db.get(models.AICommentEdit, edit_id)

def get_latest_ai_suggestion_for_comment(db: Session, comment_id: int) -> Optional[models.AICommentEdit]:
    """
    Retrieves the most recent 'suggested' AI edit for a comment.
    """
    statement = (
        select(models.AICommentEdit)
        .where(models.AICommentEdit.comment_id == comment_id)
        .where(models.AICommentEdit.status == "suggested") # Or whatever the initial status is
        .order_by(models.AICommentEdit.api_call_timestamp.desc())
    )
    return db.exec(statement).first()

def update_ai_comment_edit_status(
    db: Session,
    edit_id: int,
    status: str,
    user_final_text: Optional[str] = None
) -> Optional[models.AICommentEdit]:
    """
    Updates the status of an AICommentEdit record (e.g., 'accepted', 'rejected', 'edited_and_accepted').
    Optionally updates the user_final_edited_text.
    """
    db_ai_edit = db.get(models.AICommentEdit, edit_id)
    if db_ai_edit:
        db_ai_edit.status = status
        if user_final_text is not None:
            db_ai_edit.user_final_edited_text = user_final_text
        db.add(db_ai_edit)
        db.commit()
        db.refresh(db_ai_edit)
        return db_ai_edit
    return None

def delete_comment(db: Session, comment_id: int, user_id: int) -> Optional[models.Comment]:
    """
    Soft deletes a comment.
    Only the author or a moderator should be able to delete.
    """
    db_comment = db.get(models.Comment, comment_id)
    # Add role checks if implementing moderators
    if db_comment and db_comment.user_id == user_id and not db_comment.is_deleted:
        db_comment.is_deleted = True
        db_comment.displayed_text = "This comment has been deleted." # Or some placeholder
        db.add(db_comment)
        db.commit()
        db.refresh(db_comment)
        return db_comment
    return None
