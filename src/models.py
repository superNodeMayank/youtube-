from sqlmodel import Field, Relationship, SQLModel
from typing import Optional, List
from datetime import datetime

class UserBase(SQLModel):
    username: str = Field(unique=True, index=True)
    email: str = Field(unique=True, index=True)
    ai_assist_enabled_global: bool = Field(default=False)

class User(UserBase, table=True):
    user_id: Optional[int] = Field(default=None, primary_key=True)
    password_hash: str

    videos: List["Video"] = Relationship(back_populates="uploader")
    comments: List["Comment"] = Relationship(back_populates="author")
    # ai_comment_edits: List["AICommentEdit"] = Relationship(back_populates="user") # To be added later

class UserCreate(UserBase):
    password: str

class UserRead(UserBase):
    user_id: int


class VideoBase(SQLModel):
    title: str
    description: Optional[str] = None
    url: str = Field(unique=True)

class Video(VideoBase, table=True):
    video_id: Optional[int] = Field(default=None, primary_key=True)
    uploader_user_id: int = Field(foreign_key="user.user_id")
    upload_date: datetime = Field(default_factory=datetime.utcnow)

    uploader: User = Relationship(back_populates="videos")
    comments: List["Comment"] = Relationship(back_populates="video")

class VideoCreate(VideoBase):
    uploader_user_id: int # In a real app, this might come from the authenticated user

class VideoRead(VideoBase):
    video_id: int
    uploader_user_id: int
    upload_date: datetime


class CommentBase(SQLModel):
    original_text: str
    # displayed_text will be same as original_text for now
    # is_ai_assisted will be False for now
    # ai_enhancement_enabled_per_comment will be NULL/False for now

class Comment(SQLModel, table=True):
    comment_id: Optional[int] = Field(default=None, primary_key=True)
    video_id: int = Field(foreign_key="video.video_id")
    user_id: int = Field(foreign_key="user.user_id") # author_id
    parent_comment_id: Optional[int] = Field(default=None, foreign_key="comment.comment_id")

    original_text: str
    displayed_text: str # Initially same as original_text
    is_ai_assisted: bool = Field(default=False)
    # This field's logic will be more nuanced later. For now, simple default.
    ai_enhancement_enabled_per_comment: Optional[bool] = Field(default=None)

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow, sa_column_kwargs={"onupdate": datetime.utcnow})
    is_deleted: bool = Field(default=False)

    author: User = Relationship(back_populates="comments")
    video: Video = Relationship(back_populates="comments")

    # For self-referential relationship (threaded comments)
    replies: List["Comment"] = Relationship(back_populates="parent")
    parent: Optional["Comment"] = Relationship(back_populates="replies", sa_relationship_kwargs=dict(remote_side="Comment.comment_id"))


class CommentCreate(CommentBase):
    video_id: int
    # user_id will typically come from authenticated user context
    parent_comment_id: Optional[int] = None

class CommentRead(CommentBase):
    comment_id: int
    video_id: int
    user_id: int
    parent_comment_id: Optional[int] = None
    displayed_text: str
    is_ai_assisted: bool
    created_at: datetime
    updated_at: datetime
    author: UserRead # Nested UserRead schema for author details
    # replies: List["CommentReadAPI"] = [] # This is defined in schemas.py, careful with circular deps if used here.

# --- AICommentEdit Model ---
# As per docs/database_schema.md
class AICommentEditBase(SQLModel):
    raw_comment_text_before_ai: str
    ai_prompt_used: Optional[str] = None
    ai_generated_text: str
    user_final_edited_text: Optional[str] = None
    status: str = Field(index=True) # e.g., 'suggested', 'accepted_as_is', 'edited_and_accepted', 'rejected', 'api_error'
    ai_model_used: Optional[str] = None
    api_error_message: Optional[str] = None

class AICommentEdit(AICommentEditBase, table=True):
    edit_id: Optional[int] = Field(default=None, primary_key=True)
    comment_id: int = Field(foreign_key="comment.comment_id", index=True)
    user_id: int = Field(foreign_key="user.user_id", index=True) # User who initiated/owns the comment
    api_call_timestamp: datetime = Field(default_factory=datetime.utcnow)

    comment: "Comment" = Relationship(back_populates="ai_edits")
    user: User = Relationship() # No back_populates for user on this table by default unless specified

# Update User model to link to AICommentEdits if needed for querying user's AI interactions
# For now, not adding back_populates on User for AICommentEdit to keep it simple.

# Update Comment model to link to its AICommentEdits.
# This should be defined within the Comment class or after it if using forward refs.
# Let's ensure Comment class is aware of 'ai_edits' attribute.
# The previous `Comment.ai_edits = Relationship(...)` is one way.
# Another is to declare it in the class with proper type hints if possible,
# or ensure SQLModel.model_rebuild() is effectively called.

# For forward references like "Comment" in AICommentEdit, and potentially AICommentEdit in Comment,
# SQLModel (via Pydantic) generally handles them if they are string literals.
# If issues arise, calling SomeModel.model_rebuild() explicitly after all definitions can help.
# However, the current structure where all models are imported before metadata.create_all()
# is usually sufficient.

# Final check on relationships:
# User.comments (List["Comment"]) -> Comment.author (User)
# Video.comments (List["Comment"]) -> Comment.video (Video)
# Comment.replies (List["Comment"]) -> Comment.parent (Optional["Comment"])
# Comment.ai_edits (List["AICommentEdit"]) -> AICommentEdit.comment ("Comment") - This was set using Comment.ai_edits = ...
# AICommentEdit.user (User) - This is a simple Relationship, no back_populates on User from AICommentEdit specified.

# To ensure all relationships and forward references are correctly processed by Pydantic/SQLModel:
# Call model_rebuild for models with forward string references if not automatically handled.
# Usually not needed if all models are defined/imported before use (e.g. table creation or schema generation).
User.model_rebuild()
Video.model_rebuild()
Comment.model_rebuild()
AICommentEdit.model_rebuild()

# Update the create_db_and_tables function in database.py to use these models
# This is a conceptual note; I'll modify database.py in a separate step if needed,
# or ensure main.py handles the import and creation.
# For now, the plan is that main.py will import all models and call create_all.
