# YouTube Comment AI Enhancement

This project implements an AI-assisted comment enhancement feature for a YouTube-like platform.

## Features

-   Global toggle for AI-assisted comments in user settings.
-   Per-comment "Enhance via AI" button.
-   Integration with Gemini AI to polish comments.
-   UI flow to review, edit, or cancel AI suggestions.
-   Storage of original and AI-edited comments.
-   "AI-assisted" badge on enhanced comments.

## Project Structure

-   `src/`: Contains the main source code for the FastAPI application.
    -   `main.py`: FastAPI application entry point, defining API endpoints.
    -   `auth.py`: Authentication logic (password hashing, JWT).
    -   `config.py`: Configuration management (environment variables).
    -   `crud.py`: CRUD (Create, Read, Update, Delete) operations for database models.
    -   `database.py`: Database engine setup and session management.
    -   `models.py`: SQLModel definitions for database tables (User, Video, Comment, AICommentEdit).
    -   `schemas.py`: Pydantic schemas for API request/response validation and serialization.
    -   `ai_services.py`: Service for interacting with the Google Gemini API.
-   `tests/`: Contains unit and integration tests.
    -   `unit/`: Unit tests for individual modules (auth, crud, ai_services).
    -   `integration/`: Integration tests for API endpoints, using TestClient and an in-memory SQLite DB.
        - `conftest.py`: Pytest fixtures for test setup (DB, TestClient).
-   `docs/`: Project documentation.
    -   `database_schema.md`: Details of the database schema.
    -   `ui_mockups.md`: Textual descriptions of UI elements for the AI-assist feature.
-   `.env.example`: Example environment file (copy to `.env` for local development).
-   `requirements.txt`: Python dependencies.
-   `AGENTS.md`: Instructions for AI agents working on this project.

## Setup and Running the Application

1.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    cd <repository-name>
    ```

2.  **Create a Python virtual environment:**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Set up environment variables:**
    *   Copy `src/.env.example` to a new file named `.env` in the **project root directory**.
        ```bash
        cp src/.env.example .env
        ```
    *   Edit the `.env` file and provide necessary values:
        *   `DATABASE_URL`: Defaults to `sqlite:///./youtube_comments.db` (a local SQLite file). You can change this to a PostgreSQL URL if preferred (e.g., `postgresql://user:password@host:port/dbname`).
        *   `SECRET_KEY`: A strong secret key for JWT token encoding. Generate one (e.g., using `openssl rand -hex 32`).
        *   `ALGORITHM`: JWT algorithm (default is `HS256`).
        *   `ACCESS_TOKEN_EXPIRE_MINUTES`: JWT token expiry time.
        *   `GEMINI_API_KEY`: Your Google Gemini API key. This is required for the AI enhancement features to work. Obtain this from [Google AI Studio](https://aistudio.google.com/).
        *   `MAX_COMMENT_LENGTH`: Maximum allowed character length for comments (default: 5000). Used to validate AI suggestions and user edits.

5.  **Run the application:**
    ```bash
    uvicorn src.main:app --reload --port 8000
    ```
    The application will be available at `http://localhost:8000`.
    API documentation (Swagger UI) will be at `http://localhost:8000/docs`.
    Alternative API documentation (ReDoc) will be at `http://localhost:8000/redoc`.

    The first time you run the application, the SQLite database file (`youtube_comments.db` by default) and its tables will be created automatically in the project root.

## Running Tests

Ensure you have development dependencies installed, including `pytest`:
```bash
pip install pytest httpx # httpx is used by TestClient
```

1.  **Run all unit tests:**
    ```bash
    python -m unittest discover tests/unit
    # or if pytest is configured for unittest discovery
    # pytest tests/unit/
    ```

2.  **Run all integration tests (uses pytest):**
    ```bash
    pytest tests/integration/
    ```
    Integration tests use an in-memory SQLite database, so they won't affect your development database.

## Key AI-Assist Feature API Endpoints

-   `PUT /users/me/settings`: Update user settings, including the global AI-assist toggle (`ai_assist_enabled_global`).
-   `POST /comments/{comment_id}/enhance`: Request AI enhancement for a specific comment. Returns the AI suggestion.
-   `PUT /ai-suggestions/{suggestion_id}/review`: Accept, edit, or reject an AI suggestion. Updates the comment's displayed text and AI-assisted status.

(Refer to `http://localhost:8000/docs` for full API details when the application is running.)

## Contributing

Contributions are welcome! Please follow standard coding practices and ensure tests pass before submitting a pull request.Tool output for `create_file_with_block`:
