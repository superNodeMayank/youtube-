# Future Enhancements

This document lists potential future enhancements for the AI-assisted comment feature and the broader application.

## AI-Assist Feature Specific:

1.  **Reporting Bad AI Suggestions:**
    *   Allow users to report AI suggestions they find inappropriate, nonsensical, or unhelpful.
    *   This would involve a new API endpoint and a system for reviewing these reports to improve prompt engineering or AI model interactions.
    *   UI: A "Report suggestion" button/link in the review modal or next to AI-assisted comments.

2.  **Advanced "Undo" for Rejected Suggestions:**
    *   Currently, rejecting an AI suggestion reverts `displayed_text` to `original_text` if the comment was AI-assisted.
    *   A more advanced system could revert to the `displayed_text` that existed *before* the current enhancement cycle began, especially if a user manually edited a comment after a previous AI enhancement. This would require storing snapshots or a more detailed history of `displayed_text`.

3.  **Store and Display Text Diffs:**
    *   In the `AIEnhancementLog`, store a diff (e.g., using `difflib` output) between `raw_comment_text_before_ai` and `ai_generated_text` (and `user_final_edited_text`).
    *   The UI could then visually highlight changes in the review modal, making it easier for users to see what the AI modified.

4.  **Per-Comment AI Opt-Out/Opt-In on Creation:**
    *   Extend `CommentCreateAPI` schema to include a boolean flag (e.g., `enable_ai_assist_for_this_comment`).
    *   If global AI is ON, this flag could allow opting out for a specific new comment.
    *   If global AI is OFF, this flag could allow opting in for a specific new comment.
    *   This would enable more nuanced control beyond the explicit "Enhance via AI" button after posting.

5.  **Configurable Default Prompts:**
    *   Allow administrators or potentially users (if appropriate) to customize the default prompts sent to the Gemini API for comment enhancement, possibly based on categories or contexts.

6.  **Support for Different Enhancement Types:**
    *   Beyond a general "enhance," offer specific transformations like "make more polite," "make funnier," "check grammar," "summarize (for long comments before posting)." This would involve different prompts and potentially UI options.

## Application-Wide / Performance / Operational:

7.  **Rate Limiting for AI API Calls:**
    *   Implement robust rate limiting (e.g., per user, per IP, globally) for the `/enhance` endpoint to prevent abuse and manage Gemini API costs.
    *   Use a library like `slowapi` integrated with FastAPI.

8.  **Asynchronous AI Service Calls:**
    *   Modify `ai_services.py` to use an asynchronous HTTP client if the `google-generativeai` library or underlying API calls support it, or run synchronous calls in a thread pool executor (`FastAPI.run_in_threadpool`).
    *   This would prevent blocking the main application threads during external API calls.

9.  **Robust Handling of Concurrent Enhancement Requests:**
    *   For high-traffic scenarios, implement a queuing system (e.g., Celery, RQ) for AI enhancement requests to manage load on the AI service and provide better resilience.

10. **Advanced Monitoring and Alerting:**
    *   Integrate detailed monitoring for AI API call latency, error rates, and costs.
    *   Set up alerts for unusual patterns or high failure rates from the AI service.

11. **User Privacy Setting for AI Badge:**
    *   Allow users a privacy setting to disable the "AI-Assisted" badge on their comments, even if they used the feature.

12. **Moderation Tools for AI-Generated Content:**
    *   Consider if moderators need special tools or views to identify and review AI-assisted comments, especially if automated enhancement becomes more prevalent.

These enhancements can be prioritized based on user feedback, platform goals, and resource availability.
