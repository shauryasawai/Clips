from pydantic_settings import BaseSettings
from typing import Optional
import os

class Settings(BaseSettings):
    # Database configuration with fallback
    database_url: str = os.getenv(
        "DATABASE_URL", 
        "postgresql://user:password@localhost:5432/clips_db"
    )
    
    # Security
    secret_key: str = os.getenv(
        "SECRET_KEY", 
        "clips-api-secret-key-change-in-production"
    )
    
    # Environment
    environment: str = os.getenv("ENVIRONMENT", "production")
    
    # Vercel-specific settings
    vercel_url: str = os.getenv("VERCEL_URL", "")
    vercel_region: str = os.getenv("VERCEL_REGION", "unknown")
    
    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()