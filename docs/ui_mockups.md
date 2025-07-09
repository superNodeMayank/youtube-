# UI Mockups for AI-Assisted Comment Enhancement (Textual Descriptions)

This document describes the conceptual UI elements and user flow for the AI-assisted comment enhancement feature.

## 1. Global AI-Assist Toggle

-   **Location:** User Profile Settings page (e.g., under "Preferences" or "Comment Settings").
-   **UI Element:** A standard toggle switch.
    -   **Label:** "Enable AI-Assist for Comments"
    -   **Description (below or tooltip):** "When enabled, you'll see options to enhance your comments using AI. You can still control this for each comment individually."
    -   **States:**
        -   **ON:** AI features are available/potentially defaulted.
        -   **OFF:** AI features are hidden or less prominent. The "Enhance via AI" button might still be available but require explicit interaction.
-   **Interaction:** User clicks the toggle. Setting is saved via `PUT /users/me/settings` API endpoint. A success/error toast notification confirms the action.

## 2. "Enhance via AI" Button

-   **Location:**
    -   Near the comment input box when typing a new comment.
    -   In a comment's action menu (e.g., three-dot menu) for already posted comments by the user.
-   **UI Element:** A button or icon button (e.g., a "sparkle" or "magic wand" icon).
    -   **Label (if text button):** "Enhance with AI" or "AI Enhance"
    -   **Tooltip (if icon button):** "Enhance this comment with AI"
-   **Visibility:**
    -   Prominently visible if the user has AI-assist globally enabled.
    -   Potentially less prominent or requiring an extra click if globally disabled but still available.
    -   Only visible for the user's own comments (for editing existing ones).
-   **Interaction:**
    -   User clicks the button.
    -   The current comment text (either from input field or existing comment's `original_text`) is sent to `POST /comments/{comment_id}/enhance`.
    -   **Loading State:** Button becomes disabled, and a visual indicator (e.g., spinner icon on the button, or a small overlay/text like "Enhancing..." near the comment area) appears to signify processing.
    -   On success (`200 OK` from `/enhance`), the Suggestion Review Modal (see below) is displayed. The loading state is removed.
    -   On failure (e.g., `503` from `/enhance` due to AI service error, or `4xx` errors), an error message is shown (see Error Handling section). The button re-enables, and loading state is removed.

## 3. Suggestion Review Modal

-   **Trigger:** Appears after a successful response from `POST /comments/{comment_id}/enhance` (which returns the `log_id` and `suggested_enhanced_text`).
-   **Layout:** A modal dialog.
-   **Content:**
    -   **Title:** "AI Suggestion" or "Enhance Comment"
    -   **Side-by-Side Display (or clear visual diff, e.g., using a library like `diff-match-patch` for highlighting changes):**
        -   **Left Pane/Top Section (Label: "Your Original Comment"):** Displays the `original_text` (read-only).
        -   **Right Pane/Bottom Section (Label: "AI Enhanced Suggestion"):**
            -   Displays an editable text area.
            -   Pre-filled with `suggested_enhanced_text` from the API response.
            -   A character count (e.g., "250/5000") is displayed below the text area, updating live, reflecting `MAX_COMMENT_LENGTH`. If current length exceeds max, the count is shown in red, and "Save Edits" / "Use Suggestion" buttons might be disabled (see below).
    -   **Action Buttons:**
        -   **"Use Suggestion" / "Accept AI Version":**
            -   Calls `PUT /ai-enhancement-logs/{log_id}/review` with `{"action": "accept_as_is"}`.
            -   **Disabled if:** `suggested_enhanced_text` (from AI) exceeds `MAX_COMMENT_LENGTH`. A small message like "Suggestion is too long" appears below the text area.
            -   **Loading State:** Buttons in modal might disable; show spinner overlay on modal.
            -   Closes modal on success; comment is posted/updated with AI text.
            -   If API returns error (e.g., length validation failed on backend due to unforeseen issue, or other server error), displays error in modal's Error Message Area.
        -   **"Save Edits" / "Accept My Edit":** (Enabled if user modifies the AI suggestion text area)
            -   Calls `PUT /ai-enhancement-logs/{log_id}/review` with `{"action": "edit_and_accept", "edited_text": "<user's modified text>"}`.
            -   **Disabled if:** User's modified text in the text area exceeds `MAX_COMMENT_LENGTH`.
            -   **Loading State:** Buttons in modal might disable; show spinner overlay on modal.
            -   Closes modal on success; comment is posted/updated with user's modified AI text.
            -   If API returns error (e.g., edited text still too long on a backend double-check, or other server error), displays error in modal's Error Message Area.
        -   **"Keep Original" / "Reject Suggestion" / "Cancel":**
            -   Calls `PUT /ai-enhancement-logs/{log_id}/review` with `{"action": "reject"}`.
            -   Closes modal. If it was a new comment, user can post original or discard. If an existing comment, it remains unchanged or reverts to original.
    -   **Error Message Area:** A designated space within the modal (e.g., at the bottom, above action buttons) to display errors from the review step (e.g., "Edited text is too long (max X characters). Please shorten it.").
    -   **Optional:** A small "Powered by Gemini" or similar attribution.

## 4. "AI-Assisted" Badge

-   **Location:** Displayed next to or below a comment that has been enhanced by AI (i.e., `Comment.is_ai_assisted` is true).
-   **UI Element:** A small, unobtrusive text badge or icon + text.
    -   **Text:** "AI-Assisted" or "✨ Enhanced" (Concise for mobile, potentially more descriptive on desktop if space allows).
-   **Tooltip (on hover over badge):**
    -   "This comment was enhanced using AI assistance. The original text may have been modified for clarity, tone, or style."
    -   If the user is the author: "This comment was enhanced with AI. You can manage AI-assist settings [here (link to settings)] or re-enhance/edit your comment options."
-   **Responsiveness:** Badge should be compact. On smaller screens, an icon might be sufficient with the tooltip providing full text.

## 5. Per-Comment AI Toggle (Conceptual Client-Side Control)

-   **Purpose:** Allows user to opt-out of potential auto-enhancement for a specific comment if global AI-assist is ON, or opt-in if global is OFF but "Enhance" button is still available. This is primarily a client-side affordance.
-   **Location:** Near the comment input box, possibly below it or as an option before posting.
-   **UI Element:** A checkbox or a small toggle.
    -   **Label:** "Suggest AI enhancement for this comment" or "Enable AI for this comment".
-   **Behavior:**
    -   Influences client-side logic (e.g., whether to automatically call `/enhance` after typing, or how the "Enhance" button is presented).
    -   Not directly tied to a backend field on comment creation in the current design, but could be if auto-enhancement on initial post was a feature.

## 6. Error Handling in UI (General)

-   **Scenario 1: AI Enhancement Call Fails (`POST /comments/{comment_id}/enhance`)**
    -   **UI Feedback:**
        -   **Toast Notification or Inline Message near "Enhance" button:**
            -   Generic: "AI enhancement failed. Please try again later."
            -   Specific (if backend provides details, though 503 is generic): "Could not connect to AI service."
            -   Content Policy Block: "AI suggestion could not be provided due to content policy. Your original comment was not sent."
        -   **Button State:** "Enhance via AI" button re-enables. Loading indicator stops.
    -   **Action:** User should be able to proceed with their original comment or try enhancing again later.

-   **Scenario 2: Review/Acceptance Call Fails (`PUT /ai-enhancement-logs/{log_id}/review`)**
    -   **UI Feedback (within Suggestion Review Modal's Error Message Area):**
        -   Length Validation (400 error from backend): "Text is too long. Maximum length is {MAX_COMMENT_LENGTH} characters. Please shorten it or reject the suggestion."
        -   Generic Server Error (500 error): "Failed to save your choice. Please try again."
        -   Other 4xx errors: Display the error detail from the API response if user-friendly.
        -   **Button State:** Action buttons in modal re-enable (unless the error is unrecoverable without closing modal). Loading indicator stops.
    -   **Action:** User can modify their text (if applicable for length error) and retry, or cancel out of the modal.

These descriptions should provide a solid foundation for front-end developers to build the user interface for the AI-assisted comment enhancement feature.Tool output for `overwrite_file_with_block`:
