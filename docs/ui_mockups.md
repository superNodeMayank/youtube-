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
-   **Interaction:** User clicks the toggle. Setting is saved via `PUT /users/me/settings` API endpoint.

## 2. "Enhance via AI" Button

-   **Location:**
    -   Near the comment input box when typing a new comment.
    -   In a comment's action menu (e.g., three-dot menu) for already posted comments by the user.
-   **UI Element:** A button or icon button (e.g., a "sparkle" or "magic wand" icon).
    -   **Label (if text button):** "Enhance with AI" or "AI Enhance"
    -   **Tooltip (if icon button):** "Enhance this comment with AI"
-   **Visibility:**
    -   Always visible if the user has AI-assist globally enabled.
    -   Potentially less prominent or requiring an extra click if globally disabled but still available.
    -   Only visible for the user's own comments (for editing existing ones).
-   **Interaction:**
    -   User clicks the button.
    -   The current comment text (either from input field or existing comment's `original_text`) is sent to `POST /comments/{comment_id}/enhance`.
    -   A loading state is shown (e.g., button disabled, spinner).
    -   On success, the Suggestion Review Modal (see below) is displayed.
    -   On failure (e.g., API error), an error message is shown (see Error Handling).

## 3. Suggestion Review Modal

-   **Trigger:** Appears after a successful response from `POST /comments/{comment_id}/enhance`.
-   **Layout:** A modal dialog.
-   **Content:**
    -   **Title:** "AI Suggestion" or "Enhance Comment"
    -   **Side-by-Side Display (or clear visual diff):**
        -   **Left Pane/Top Section (Label: "Your Original Comment"):** Displays the `original_text` (read-only).
        -   **Right Pane/Bottom Section (Label: "AI Enhanced Suggestion"):**
            -   Displays an editable text area.
            -   Pre-filled with `suggested_enhanced_text` from the API response.
    -   **Action Buttons:**
        -   **"Use Suggestion" / "Accept AI Version":**
            -   Calls `PUT /ai-suggestions/{suggestion_id}/review` with `{"action": "accept_as_is"}`.
            -   Closes modal, comment is posted/updated with AI text.
        -   **"Save Edits" / "Accept My Edit":** (Enabled if user modifies the AI suggestion text area)
            -   Calls `PUT /ai-suggestions/{suggestion_id}/review` with `{"action": "edit_and_accept", "edited_text": "<user's modified text>"}`.
            -   Closes modal, comment is posted/updated with user's modified AI text.
        -   **"Keep Original" / "Reject Suggestion" / "Cancel":**
            -   Calls `PUT /ai-suggestions/{suggestion_id}/review` with `{"action": "reject"}`.
            -   Closes modal. If it was a new comment, user can post original or discard. If an existing comment, it remains unchanged or reverts to original.
    -   **Optional:** A small "Powered by Gemini" or similar attribution.

## 4. "AI-Assisted" Badge

-   **Location:** Displayed next to or below a comment that has been enhanced by AI (i.e., `Comment.is_ai_assisted` is true).
-   **UI Element:** A small, unobtrusive text badge or icon + text.
    -   **Text:** "AI-Assisted" or "✨ Enhanced"
-   **Tooltip (on hover over badge):**
    -   "This comment was enhanced with AI assistance."
    -   If the user is the author: "This comment was enhanced with AI. You can manage AI-assist settings [here (link to settings) / in your comment options]."

## 5. Per-Comment AI Toggle (Conceptual Client-Side Control)

-   **Purpose:** Allows user to opt-out of potential auto-enhancement for a specific comment if global AI-assist is ON, or opt-in if global is OFF but "Enhance" button is still available. This is primarily a client-side affordance influencing whether the "Enhance via AI" flow is automatically triggered or if the button is shown differently.
-   **Location:** Near the comment input box, possibly below it.
-   **UI Element:** A checkbox.
    -   **Label:** "Suggest AI enhancement for this comment" or "Enable AI for this comment".
-   **Behavior:**
    -   If global AI is ON, this checkbox might be checked by default. Unchecking it prevents any automatic suggestion flow for this specific comment.
    -   If global AI is OFF, this checkbox might be unchecked. Checking it could make the "Enhance via AI" button more prominent or enable a specific workflow.
    -   The state of this checkbox would influence client-side logic rather than directly sending a boolean to the backend on comment creation, unless the `CommentCreateAPI` schema is extended. The current backend design relies on explicit calls to `/enhance`.

## 6. Error Handling in UI (Related to AI Feature)

-   **Scenario:** AI enhancement call fails (e.g., API error from Gemini, network issue, content blocked).
-   **UI Feedback:**
    -   **Toast Notification or Inline Message:**
        -   "AI enhancement failed. Please try again later."
        -   "Could not generate AI suggestion. Your original comment has not been changed."
        -   If content blocked: "AI suggestion could not be provided due to content policy."
    -   **Button State:** "Enhance via AI" button might re-enable after a short delay if a retry is appropriate.
-   **Action:** User should be able to proceed with their original comment or try enhancing again later.

These descriptions should provide a solid foundation for front-end developers to build the user interface for the AI-assisted comment enhancement feature.
