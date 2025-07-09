# Agent Instructions for YouTube Comment AI Enhancement Project

## Overview

This document provides instructions and guidelines for AI agents working on this project.

## Coding Conventions

-   **Language:** Python (version 3.9+).
-   **Style Guide:** Adhere to PEP 8. Use a linter (e.g., Flake8) and a formatter (e.g., Black) to maintain consistency.
-   **Modularity:** Design components to be modular and reusable.
-   **Error Handling:** Implement robust error handling. Use specific exception types where appropriate.
-   **Logging:** Use the `logging` module for application logs. Configure log levels appropriately for development and production.

## Development Process

1.  **Branching:** Create a new feature branch for each distinct piece of functionality. Branch names should be descriptive (e.g., `feature/ai-comment-toggle`).
2.  **Commits:** Write clear and concise commit messages. Follow conventional commit message formats if possible.
3.  **Testing:**
    -   Write unit tests for all new functions and classes. Aim for high test coverage.
    -   Write integration tests for interactions between components, especially API endpoints and database operations.
    -   Ensure all tests pass before submitting code for review.
4.  **Documentation:**
    -   Update `README.md` with any changes to setup, features, or usage.
    -   Document new API endpoints, database schemas, and complex logic.
    -   Add comments to code where necessary to clarify complex sections.
5.  **Pull Requests (PRs):**
    -   Ensure your PR includes a clear description of the changes made.
    -   Link to any relevant issues.
    -   Confirm that all automated checks (linters, tests) pass.

## Key Technologies (Planned)

-   **Backend Framework:** (To be decided - e.g., Flask, FastAPI)
-   **Database:** (To be decided - e.g., PostgreSQL, MySQL, SQLite for development)
-   **AI Model API:** Google Gemini API
-   **Frontend:** (Conceptual for now - UI will be described, not implemented by this agent)

## Specific Instructions for AI-Assist Feature

-   **Gemini API Key:** Store the Gemini API key securely. Do not hardcode it. Use environment variables.
-   **Prompt Engineering:** The quality of the AI-enhanced comment depends heavily on the prompt. The raw user comment will be the primary input. Consider if any standard prefix or suffix to the prompt would improve results (e.g., "Rewrite this YouTube comment to be more polite and constructive, while preserving the original intent: [user's comment]").
-   **Data Privacy:**
    -   Clearly indicate to users when AI is being used.
    -   Ensure users can opt-out of the feature.
    -   Do not store any personally identifiable information (PII) beyond what's necessary for the comment system (user ID, comment text).
-   **Transparency:**
    -   Visually distinguish AI-assisted comments (e.g., with a badge).
    -   Allow users to see their original comment if an AI suggestion is made.
-   **Rate Limiting:** Implement rate limiting for calls to the Gemini API to prevent abuse and manage costs. This should be configurable.
-   **Error Handling for AI:**
    -   If the AI API call fails, the system should gracefully fall back (e.g., allow the user to post their original comment, or try again later).
    -   If the AI returns an inappropriate or nonsensical response, the user should be able to discard it easily.

## Environment Setup (Agent Responsibility)

-   The agent is responsible for setting up its own development environment, including installing Python, pip, and any necessary libraries.
-   The agent should be able to create and manage virtual environments.
-   The agent should use `requirements.txt` to manage dependencies. If new dependencies are added, update this file.

## Initial File Structure (Agent Created)

-   `src/`
-   `tests/`
-   `docs/`
-   `README.md`
-   `AGENTS.md`

This `AGENTS.md` file can be updated as the project evolves. If you have suggestions for improving these guidelines, please include them in your work.
