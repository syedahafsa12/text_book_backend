from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv
import logging

load_dotenv()
logger = logging.getLogger(__name__)

# Use SQLite for local development, or Postgres if DATABASE_URL is set
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./sql_app.db")

# Ensure Postgres URL is correct for SQLAlchemy (postgres:// -> postgresql://)
if SQLALCHEMY_DATABASE_URL.startswith("postgres://"):
    SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Lazy initialization for Vercel serverless
engine = None
SessionLocal = None
Base = declarative_base()

def init_db():
    """Initialize database connection (lazy loading for serverless)"""
    global engine, SessionLocal
    
    if engine is None:
        try:
            connect_args = {"check_same_thread": False} if "sqlite" in SQLALCHEMY_DATABASE_URL else {}
            engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args=connect_args)
            SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
            logger.info("Database initialized successfully")
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            SessionLocal = sessionmaker()
    
    return engine, SessionLocal

def get_db():
    """Dependency for getting database session"""
    init_db()  # Ensure DB is initialized
    if SessionLocal is None:
        yield None
        return
    
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
