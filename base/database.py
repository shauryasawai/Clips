from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from .config import settings
import logging
import os

logger = logging.getLogger(__name__)

def create_supabase_connection_string():
    """Create optimized connection string for Supabase"""
    original_url = settings.database_url
    
    if "supabase.co" in original_url:
        if "?" in original_url:
            base_url = original_url.split("?")[0]
        else:
            base_url = original_url
        
        # Add Supabase-optimized parameters
        optimized_url = f"{base_url}?sslmode=require&connect_timeout=30"
        logger.info("🔧 Using Supabase-optimized connection string")
        return optimized_url
    
    return original_url

def create_database_engine():
    """Create database engine optimized for Supabase + Vercel"""
    try:
        connection_string = create_supabase_connection_string()
        
        engine = create_engine(
            connection_string,
            # Serverless optimizations
            pool_size=0,              # No connection pool for serverless
            max_overflow=0,           # No overflow connections  
            pool_pre_ping=False,      # Disable ping for serverless
            pool_recycle=-1,          # Don't recycle connections
            echo=False,               # Disable logging for performance
            connect_args={
                "connect_timeout": 30,
                "application_name": "clips-api-vercel",
                "options": "-c statement_timeout=30s"
            }
        )
        
        logger.info("✅ Database engine created for Supabase")
        return engine
        
    except Exception as e:
        logger.error(f"❌ Failed to create database engine: {e}")
        raise Exception(f"Database connection failed: {str(e)}")

try:
    engine = create_database_engine()
    logger.info("🗄️ Database engine initialized successfully")
except Exception as e:
    logger.error(f"⚠️ Database engine initialization failed: {e}")
    engine = None

# Create session factory only if engine exists
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine) if engine else None
Base = declarative_base()

def get_db():
    """Database dependency with connection retry logic"""
    if not engine:
        raise Exception("Database engine not initialized")
    
    db = None
    max_retries = 3
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            db = SessionLocal()
            db.execute("SELECT 1")
            yield db
            break
            
        except Exception as e:
            retry_count += 1
            logger.error(f"Database connection attempt {retry_count}/{max_retries} failed: {e}")
            
            if db:
                db.close()
                db = None
            
            if retry_count >= max_retries:
                raise Exception(f"Database connection failed after {max_retries} attempts: {str(e)}")
            
            import time
            time.sleep(0.5 * retry_count)
    
    try:
        if db:
            yield db
    except Exception as e:
        logger.error(f"Database session error: {e}")
        if db:
            db.rollback()
        raise
    finally:
        if db:
            db.close()