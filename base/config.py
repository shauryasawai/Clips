from pydantic_settings import BaseSettings
from typing import Optional
import os

class Settings(BaseSettings):
    # Vercel environment variables
    database_url: str = os.getenv("DATABASE_URL", "postgresql://user:password@localhost:5432/clips_db")
    secret_key: str = os.getenv("SECRET_KEY", "your-secret-key-here")
    environment: str = os.getenv("ENVIRONMENT", "production")
    
    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()