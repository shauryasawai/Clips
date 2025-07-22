from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from .config import settings

# Serverless-optimized engine configuration
engine = create_engine(
    settings.database_url,
    pool_size=1,          
    max_overflow=0,       
    pool_pre_ping=True,   
    pool_recycle=300,   
    connect_args={
        "options": "-c timezone=utc"
    } if "postgresql" in settings.database_url else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()