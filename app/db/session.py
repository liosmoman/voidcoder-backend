from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base # For model class inheritance

from app.core.config import settings # Import settings from your config.py

# Create the SQLAlchemy engine
# connect_args is often used for SQLite, for PostgreSQL it's usually not needed unless specific SSL modes etc.
engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)

# Create a SessionLocal class
# This SessionLocal class itself is not a database session yet.
# But when we call SessionLocal(), we will get an individual session.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for our SQLAlchemy models to inherit from
# All your model classes (tables) will inherit from this Base.
Base = declarative_base()

# Dependency to get DB session (used in API endpoints)
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()