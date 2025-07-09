from pydantic_settings import BaseSettings
from dotenv import load_dotenv
import os

load_dotenv()  # Load variables from .env file

class Settings(BaseSettings):
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./youtube_comments.db")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "a_very_secret_key")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))
    GEMINI_API_KEY: str | None = os.getenv("GEMINI_API_KEY")
    MAX_COMMENT_LENGTH: int = int(os.getenv("MAX_COMMENT_LENGTH", 5000)) # Default to 5000 chars

    class Config:
        env_file = ".env"
        env_file_encoding = 'utf-8'

settings = Settings()
