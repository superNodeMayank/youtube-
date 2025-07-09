from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

# Re-exporting from models.py for clarity in API layer
# These are Pydantic models because SQLModel classes are also Pydantic models.
from src.models import (
    UserBase, UserCreate, UserRead,
    VideoBase, VideoCreate, VideoRead,
    CommentBase, CommentCreate as SQLModelCommentCreate, CommentRead as SQLModelCommentRead
)

# Schemas for User Authentication
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

# Schemas for Comments API
# We might want slightly different structures for API input/output
# than the direct DB model, especially for creation.

class CommentCreateAPI(CommentBase): # User provides this
    video_id: int
    parent_comment_id: Optional[int] = None
    # user_id will be injected from the authenticated user, not provided by client in body

class CommentReadAPI(SQLModelCommentRead): # API returns this
    # SQLModelCommentRead already includes author details (UserRead)
    # We can add more fields or customize the structure if needed, e.g., replies
    # For now, it's largely the same as SQLModelCommentRead
    replies: List["CommentReadAPI"] = [] # For nested replies

# This is needed for Pydantic to correctly process the self-referencing `replies` field.
CommentReadAPI.model_rebuild()

# --- Schemas for AICommentEdit ---
from src.models import AICommentEditBase # Import base class

class AICommentEditRead(AICommentEditBase):
    edit_id: int
    comment_id: int
    user_id: int # User who authored the original comment / initiated AI edit
    api_call_timestamp: datetime
    # Could optionally include nested UserRead for the user_id

class AICommentEditCreateBody(AICommentEditBase): # What client sends to create a record (usually internal)
    # comment_id and user_id will be from path/context
    pass

class AICommentEditDBInput(AICommentEditBase): # What CRUD receives to create in DB
    comment_id: int
    user_id: int


# Schema for User Registration (if different from UserCreate, e.g. password confirmation)
class UserRegister(UserCreate):
    pass # For now, same as UserCreate

# Schema for User Login
class UserLogin(BaseModel):
    username: str # Could be email or username
    password: str


# It can be useful to have a generic message schema for simple API responses
class Message(BaseModel):
    message: str

# --- User Settings Schema ---
class UserSettingsUpdate(BaseModel):
    ai_assist_enabled_global: Optional[bool] = None
    # Add other updatable user settings here if any

# --- Schemas for AI Enhancement Flow ---
from pydantic import Field # Ensure Field is imported if not already

class EnhanceCommentRequest(BaseModel):
    # If user can provide a custom prompt template for the "Enhance via AI" button
    prompt_template: Optional[str] = Field(None, example="Make this comment funnier: {comment}")

class EnhanceCommentResponse(BaseModel):
    suggestion_id: int # This is the ai_comment_edits.edit_id
    comment_id: int
    original_text: str # The text that was sent for enhancement (comment.original_text)
    suggested_enhanced_text: str
    status: str # Should be 'suggested'

class ReviewEnhancementRequest(BaseModel):
    action: str = Field(..., pattern="^(accept_as_is|edit_and_accept|reject)$")
    # For newer Pydantic/Python, this could be: action: Literal['accept_as_is', 'edit_and_accept', 'reject']
    edited_text: Optional[str] = Field(None, description="The user's final edited text if action is 'edit_and_accept'")
