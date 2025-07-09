# Database Schema for YouTube Comment AI Enhancement

This document outlines the proposed database schema.

## Tables

### 1. `users` Table

Stores user account information and global AI-assist preferences.

-   `user_id`: INTEGER, PRIMARY KEY, AUTOINCREMENT
-   `username`: VARCHAR(255), UNIQUE, NOT NULL
-   `email`: VARCHAR(255), UNIQUE, NOT NULL
-   `password_hash`: VARCHAR(255), NOT NULL
-   `created_at`: TIMESTAMP, DEFAULT CURRENT_TIMESTAMP
-   `updated_at`: TIMESTAMP, DEFAULT CURRENT_TIMESTAMP
-   `ai_assist_enabled_global`: BOOLEAN, DEFAULT FALSE, NOT NULL (Global toggle for AI assist)

### 2. `videos` Table

Stores information about videos to which comments can be attached.

-   `video_id`: INTEGER, PRIMARY KEY, AUTOINCREMENT
-   `uploader_user_id`: INTEGER, FOREIGN KEY REFERENCES `users(user_id)`
-   `title`: VARCHAR(255), NOT NULL
-   `description`: TEXT
-   `upload_date`: TIMESTAMP, DEFAULT CURRENT_TIMESTAMP
-   `url`: VARCHAR(255), UNIQUE, NOT NULL

### 3. `comments` Table

Stores individual comments, linking them to users and videos. It holds both the original user input and the text that is ultimately displayed.

-   `comment_id`: INTEGER, PRIMARY KEY, AUTOINCREMENT
-   `video_id`: INTEGER, FOREIGN KEY REFERENCES `videos(video_id)`, NOT NULL
-   `user_id`: INTEGER, FOREIGN KEY REFERENCES `users(user_id)`, NOT NULL
-   `parent_comment_id`: INTEGER, FOREIGN KEY REFERENCES `comments(comment_id)`, NULL (For threaded comments/replies)
-   `original_text`: TEXT, NOT NULL (The raw text input by the user)
-   `displayed_text`: TEXT, NOT NULL (The text actually shown, could be original or AI-edited)
-   `is_ai_assisted`: BOOLEAN, DEFAULT FALSE, NOT NULL (Badge indicator if `displayed_text` is AI-influenced)
-   `ai_enhancement_enabled_per_comment`: BOOLEAN, DEFAULT NULL (User's choice for this specific comment. `NULL` means it follows global setting or wasn't explicitly set.)
-   `created_at`: TIMESTAMP, DEFAULT CURRENT_TIMESTAMP
-   `updated_at`: TIMESTAMP, DEFAULT CURRENT_TIMESTAMP
-   `is_deleted`: BOOLEAN, DEFAULT FALSE, NOT NULL (For soft deletes)

### 4. `AIEnhancementLog` Table (formerly `ai_comment_edits`)

Logs each instance of AI enhancement for auditing, troubleshooting, and managing the review flow.

-   `log_id`: INTEGER, PRIMARY KEY, AUTOINCREMENT (formerly `edit_id`)
-   `comment_id`: INTEGER, FOREIGN KEY REFERENCES `comments(comment_id)`, NOT NULL
-   `user_id`: INTEGER, FOREIGN KEY REFERENCES `users(user_id)`, NOT NULL (User who authored the original comment)
-   `raw_comment_text_before_ai`: TEXT, NOT NULL (The text that was sent to the AI for this specific enhancement attempt)
-   `ai_prompt_used`: TEXT (Optional, if a more complex prompt than just the raw comment is constructed)
-   `ai_generated_text`: TEXT, NOT NULL (The direct output from the AI model)
-   `user_final_edited_text`: TEXT (If the user further edits the AI suggestion before posting. `NULL` if accepted as-is or rejected.)
-   `status`: VARCHAR(50) NOT NULL (e.g., 'suggested', 'accepted_as_is', 'edited_and_accepted', 'rejected', 'api_error', 'length_error', 'cancelled_by_user')
-   `ai_model_used`: VARCHAR(100) (e.g., 'Gemini-Pro-1.0')
-   `api_call_timestamp`: TIMESTAMP, DEFAULT CURRENT_TIMESTAMP
-   `api_error_message`: TEXT (If an error occurred during the API call)

## Relationships

-   A `user` can post many `comments`.
-   A `video` can have many `comments`.
-   Each `comment` is authored by one `user` and is associated with one `video`.
-   A `comment` can be a reply to another `comment` (self-referencing `parent_comment_id`).
-   Each time a comment undergoes AI enhancement (or an attempt is made), a record is created in `AIEnhancementLog` linked to the parent `comment`.

## Notes on Specific Fields:

-   **`comments.original_text`**: Stores the user's initial raw comment. This is important for audit and if the user wants to revert or disable AI enhancement.
-   **`comments.displayed_text`**: This is what other users see. It will be the same as `original_text` if AI is not used or if the AI suggestion is rejected. Otherwise, it's the AI-enhanced (and possibly user-modified) version.
-   **`comments.is_ai_assisted`**: A boolean flag primarily for the UI to display an "AI-assisted" badge. True if `displayed_text` is different from `original_text` due to AI enhancement.
-   **`users.ai_assist_enabled_global`**: The main user preference set in their profile settings.
-   **`comments.ai_enhancement_enabled_per_comment`**: This field allows for more granular control:
    -   If a user has `ai_assist_enabled_global = TRUE`, they might still choose to disable AI for a *specific* comment (setting this to `FALSE`).
    -   If a user has `ai_assist_enabled_global = FALSE`, they can use the "Enhance via AI" button for a *specific* comment (setting this to `TRUE` for that comment).
    -   If `NULL`, the behavior defaults to the global setting or the state before an explicit per-comment action.
-   **`AIEnhancementLog.status`** (formerly `ai_comment_edits.status`): Tracks the lifecycle of an AI suggestion (e.g. whether the user accepted, edited, or rejected the AI's output). This is crucial for the UI flow and for understanding feature usage.

This schema is designed to be flexible and provide a good audit trail for the AI-assisted commenting feature. It will be translated into specific ORM models or SQL `CREATE TABLE` statements during implementation.
