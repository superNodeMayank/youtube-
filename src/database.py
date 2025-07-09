from sqlmodel import create_engine, SQLModel, Session
from src.config import settings

# The database_url without the driver prefix for SQLite, as create_engine handles it.
# For other databases like PostgreSQL, it would be e.g. "postgresql://user:password@host/dbname"
DATABASE_URL = settings.DATABASE_URL

if DATABASE_URL.startswith("sqlite"):
    # For SQLite, connect_args is used to enable foreign key constraints,
    # as they are not enabled by default.
    engine = create_engine(DATABASE_URL, echo=True, connect_args={"check_same_thread": False})
else:
    engine = create_engine(DATABASE_URL, echo=True)


def create_db_and_tables():
    # This function should be called once at startup to create tables.
    # It's important to import all models that inherit from SQLModel Base
    # *before* calling create_all, so they are registered with SQLAlchemy's metadata.
    # We will import them in main.py or a specific models module that imports all of them.
    # For now, let's import them here to ensure they are registered.
    # This assumes all models are in src.models
    from src import models # Ensure this import brings User, Video, Comment etc. into scope
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session
