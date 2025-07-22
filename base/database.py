from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from .config import settings
import logging

logger = logging.getLogger(__name__)

# Serverless-optimized engine configuration
try:
    engine = create_engine(
        settings.database_url,
        # Serverless optimizations
        pool_size=0,              # No connection pool for serverless
        max_overflow=0,           # No overflow connections
        pool_pre_ping=False,      # Skip ping in serverless
        pool_recycle=-1,          # Don't recycle connections
        echo=False,               # Disable SQL logging for performance
        # Connection arguments for better reliability
        connect_args={
            "connect_timeout": 10,
            "application_name": "clips-api-vercel"
        } if "postgresql" in settings.database_url else {}
    )
    logger.info("Database engine created successfully")
except Exception as e:
    logger.error(f"Failed to create database engine: {e}")
    raise

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    """Database dependency for FastAPI with better error handling"""
    db = None
    try:
        db = SessionLocal()
        yield db
    except Exception as e:
        logger.error(f"Database session error: {e}")
        if db:
            db.rollback()
        raise
    finally:
        if db:
            db.close()