from collections import defaultdict
from functools import wraps
from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import create_engine, text
import time
import logging
from typing import List
import os
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from fastapi.responses import Response

from . import crud, models, schemas
from .database import SessionLocal, engine
from .config import settings

# ❌ REMOVE THIS LINE FOR VERCEL - Don't create tables on import
# models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Clips API",
    description="Backend service for streaming audio clips with Supabase database - Deployed on Vercel",
    version="1.0.0",
    # Always show docs for demo purposes
    docs_url="/docs",
    redoc_url="/redoc"
)

# Enhanced CORS for Vercel
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Open for demo, restrict in production
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    max_age=600
)

# Improved database dependency with better error handling
def get_db():
    db = None
    try:
        db = SessionLocal()
        # Test the connection before yielding
        db.execute(text("SELECT 1"))
        yield db
    except Exception as e:
        logging.error(f"Database connection failed in get_db(): {e}")
        if db:
            try:
                db.rollback()
            except:
                pass
        raise HTTPException(
            status_code=503, 
            detail={
                "error": "Database connection failed",
                "message": str(e),
                "troubleshooting": "Check /debug/database for more details"
            }
        )
    finally:
        if db:
            try:
                db.close()
            except:
                pass

# Simplified logging for serverless
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# In-memory rate limiting for serverless
request_counts = defaultdict(list)

def rate_limit(max_requests: int = 100, window: int = 300):
    def decorator(func):
        @wraps(func)
        def wrapper(request: Request, *args, **kwargs):
            client_ip = request.client.host if request.client else "unknown"
            now = time.time()
            
            # Clean old requests
            request_counts[client_ip] = [
                req_time for req_time in request_counts[client_ip] 
                if now - req_time < window
            ]
            
            # Check rate limit
            if len(request_counts[client_ip]) >= max_requests:
                raise HTTPException(
                    status_code=429,
                    detail="Rate limit exceeded. Please try again later."
                )
            
            # Record this request
            request_counts[client_ip].append(now)
            
            return func(request, *args, **kwargs)
        return wrapper
    return decorator

# Simplified request logging for serverless
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    
    try:
        response = await call_next(request)
        process_time = time.time() - start_time
        
        # Simplified logging for serverless
        status_emoji = "✅" if response.status_code < 400 else "❌" 
        logger.info(f"{status_emoji} {request.method} {request.url.path} - {response.status_code} - {process_time:.3f}s")
        
        # Add Vercel-specific headers
        response.headers["X-Process-Time"] = str(process_time)
        response.headers["X-Platform"] = "Vercel"
        response.headers["X-Database"] = "Supabase"
        
        return response
        
    except Exception as e:
        process_time = time.time() - start_time
        logger.error(f"💥 {request.method} {request.url.path} - ERROR: {str(e)} - {process_time:.3f}s")
        
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal server error",
                "message": str(e),
                "timestamp": time.time(),
                "platform": "Vercel"
            }
        )

# Root endpoint with Vercel-specific information
@app.get("/", response_class=JSONResponse)
async def root():
    """API root endpoint with service information"""
    return {
        "message": "🎵 Clips API - Audio streaming service",
        "version": "1.0.0",
        "platform": "Vercel Serverless",
        "database": "Supabase PostgreSQL",
        "environment": settings.environment,
        "status": "online",
        "endpoints": {
            "documentation": "/docs",
            "health": "/health",
            "debug_env": "/debug/env",
            "debug_database": "/debug/database",
            "debug_vercel": "/debug/vercel",
            "setup_database": "/admin/setup-db",
            "seed_database": "/admin/seed-db",
            "clips": "/clips",
            "stream": "/clips/{id}/stream",
            "stats": "/clips/{id}/stats",
            "popular": "/clips/popular",
            "database_stats": "/stats"
        },
        "setup_instructions": [
            "1. Check: GET /debug/database",
            "2. Setup: POST /admin/setup-db",
            "3. Seed: POST /admin/seed-db", 
            "4. Test: GET /clips"
        ]
    }

@app.get("/metrics")
def get_metrics():
    """Prometheus metrics endpoint"""
    return Response(generate_latest(), media_type="text/plain")

# Basic health check without database dependency
@app.get("/health")
def health_check():
    """Basic health check for Vercel"""
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "platform": "Vercel Serverless",
        "region": os.getenv("VERCEL_REGION", "unknown"),
        "environment": settings.environment,
        "message": "API is running. Use /debug/database to test database connection."
    }

# Debug environment variables
@app.get("/debug/env")
def debug_environment():
    """Debug environment variables (safe version)"""
    return {
        "database_url_set": bool(settings.database_url and "supabase" in settings.database_url),
        "database_host": settings.database_url.split('@')[1].split(':')[0] if '@' in settings.database_url else "Not found",
        "secret_key_set": bool(settings.secret_key and len(settings.secret_key) > 20),
        "environment": settings.environment,
        "vercel_region": os.getenv("VERCEL_REGION", "not-set"),
        "vercel_env": os.getenv("VERCEL_ENV", "not-set"),
        "vercel_url": os.getenv("VERCEL_URL", "not-set")
    }

# Enhanced debug database connection
@app.get("/debug/database") 
def debug_database_connection():
    """Test database connection directly without dependencies"""
    try:
        # Show what URL we're trying to use (hide password)
        db_url_parts = settings.database_url.split(':')
        if len(db_url_parts) >= 3 and '@' in settings.database_url:
            password_part = settings.database_url.split(':')[2].split('@')[0]
            safe_url = settings.database_url.replace(password_part, "****")
        else:
            safe_url = "Invalid URL format"
        
        logger.info(f"Testing database connection to: {safe_url}")
        
        # Create a fresh engine for testing with optimized settings
        test_engine = create_engine(
            settings.database_url,
            pool_size=1,
            max_overflow=0,
            pool_pre_ping=True,
            connect_args={
                "connect_timeout": 30,
                "application_name": "clips-api-debug",
                "sslmode": "require"
            }
        )
        
        # Try to connect and run queries
        with test_engine.connect() as connection:
            # Test basic connection
            result = connection.execute(text("SELECT version()"))
            version = result.fetchone()
            
            # Test if clips table exists
            try:
                table_check = connection.execute(text("""
                    SELECT COUNT(*) 
                    FROM information_schema.tables 
                    WHERE table_name = 'clips' AND table_schema = 'public'
                """))
                table_exists = table_check.fetchone()[0] > 0
                
                if table_exists:
                    clip_count = connection.execute(text("SELECT COUNT(*) FROM clips")).fetchone()[0]
                else:
                    clip_count = 0
                    
            except Exception as table_error:
                table_exists = False
                clip_count = 0
                logger.warning(f"Could not check clips table: {table_error}")
            
            return {
                "status": "✅ CONNECTION SUCCESS",
                "database_url": safe_url,
                "postgresql_version": version[0][:100] if version else "Unknown",
                "clips_table_exists": table_exists,
                "clips_count": clip_count,
                "environment": settings.environment,
                "timestamp": time.time(),
                "next_steps": [
                    "Database connection is working!",
                    "Run POST /admin/setup-db to create tables" if not table_exists else "Tables exist",
                    "Run POST /admin/seed-db to add sample data" if clip_count == 0 else f"Database has {clip_count} clips"
                ]
            }
            
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Database connection test failed: {error_msg}")
        
        # Provide specific error guidance
        if "timeout" in error_msg.lower():
            suggestion = "Connection timeout - check if Supabase project is active and not paused"
        elif "authentication" in error_msg.lower() or "password" in error_msg.lower():
            suggestion = "Authentication failed - check username/password in DATABASE_URL"
        elif "does not exist" in error_msg.lower():
            suggestion = "Database does not exist - check database name in connection string"
        elif "connection refused" in error_msg.lower():
            suggestion = "Connection refused - check host and port in connection string"
        elif "ssl" in error_msg.lower():
            suggestion = "SSL connection issue - Supabase requires SSL connections"
        else:
            suggestion = "Unknown connection error - check Supabase project status"
            
        return {
            "status": "❌ CONNECTION FAILED",
            "error": error_msg,
            "database_url": safe_url if 'safe_url' in locals() else "Could not parse URL",
            "suggestion": suggestion,
            "troubleshooting_steps": [
                "1. Check if Supabase project is active (not paused)",
                "2. Verify DATABASE_URL format: postgresql://postgres:password@db.project.supabase.co:5432/postgres",
                "3. Check if password contains special characters that need URL encoding",
                "4. Ensure project allows connections (no IP restrictions)",
                "5. Verify project ID and region are correct"
            ],
            "common_solutions": {
                "paused_project": "Go to supabase.com dashboard and resume project",
                "wrong_password": "Reset database password in Supabase settings",
                "special_chars": "URL encode special characters in password",
                "ip_restrictions": "Disable IP restrictions in Supabase network settings"
            },
            "timestamp": time.time()
        }

# Vercel-specific debug endpoint
@app.get("/debug/vercel")
def vercel_debug():
    """Debug endpoint for Vercel deployment information"""
    return {
        "vercel_env": {
            "region": os.getenv("VERCEL_REGION", "not-set"),
            "url": os.getenv("VERCEL_URL", "not-set"),
            "env": os.getenv("VERCEL_ENV", "not-set"),
            "git_commit": os.getenv("VERCEL_GIT_COMMIT_SHA", "not-set")[:8] if os.getenv("VERCEL_GIT_COMMIT_SHA") else "not-set"
        },
        "app_config": {
            "environment": settings.environment,
            "database_host": settings.database_url.split('@')[1].split('/')[0] if '@' in settings.database_url else "localhost"
        },
        "platform": "Vercel Serverless",
        "timestamp": time.time()
    }

# Database health check (separate endpoint)
@app.get("/health/database")
def database_health_check(db: Session = Depends(get_db)):
    """Database connectivity health check using dependency"""
    try:
        # Test Supabase connection
        db.execute(text("SELECT 1"))
        
        # Get basic stats from Supabase
        clip_count = db.query(models.Clip).count()
        total_plays = db.query(models.Clip).with_entities(models.Clip.play_count).all()
        total_play_count = sum([play[0] for play in total_plays]) if total_plays else 0
        
        return {
            "status": "healthy",
            "timestamp": time.time(),
            "platform": "Vercel Serverless",
            "database": {
                "provider": "Supabase",
                "status": "connected",
                "host": settings.database_url.split('@')[1].split('/')[0] if '@' in settings.database_url else "localhost"
            },
            "stats": {
                "total_clips": clip_count,
                "total_plays": total_play_count
            }
        }
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        raise HTTPException(
            status_code=503, 
            detail={
                "status": "unhealthy",
                "platform": "Vercel",
                "database": "connection_failed",
                "error": str(e),
                "timestamp": time.time()
            }
        )

# Setup database tables (run this first)
@app.post("/admin/setup-db")
def setup_database():
    """Setup database tables in Supabase (run this first after deployment)"""
    try:
        # Test connection first
        test_engine = create_engine(
            settings.database_url,
            connect_args={
                "connect_timeout": 30,
                "sslmode": "require"
            }
        )
        
        with test_engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        
        # Create tables
        models.Base.metadata.create_all(bind=test_engine)
        
        # Verify table creation
        with test_engine.connect() as connection:
            result = connection.execute(text("""
                SELECT COUNT(*) 
                FROM information_schema.tables 
                WHERE table_name = 'clips' AND table_schema = 'public'
            """))
            table_exists = result.fetchone()[0] > 0
            
            if not table_exists:
                raise Exception("Table creation failed - clips table not found")
            
            # Check existing data
            existing_clips = connection.execute(text("SELECT COUNT(*) FROM clips")).fetchone()[0]
        
        return {
            "message": "✅ Database tables created successfully!",
            "clips_table_created": True,
            "existing_clips": existing_clips,
            "next_step": "Run POST /admin/seed-db to add sample data" if existing_clips == 0 else f"Database already has {existing_clips} clips",
            "platform": "Vercel",
            "database": "Supabase"
        }
        
    except Exception as e:
        logger.error(f"Database setup failed: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Database setup failed",
                "message": str(e),
                "suggestion": "Check /debug/database first to ensure connection works"
            }
        )

# Seed database with sample data (run after setup)
@app.post("/admin/seed-db")
def seed_database(db: Session = Depends(get_db)):
    """Seed Supabase database with sample clips data"""
    try:
        # Check if data already exists
        existing_clips = db.query(models.Clip).count()
        if existing_clips > 0:
            return {
                "message": "Database already has data",
                "existing_clips": existing_clips,
                "platform": "Vercel"
            }
        
        # Sample clips data with working audio URLs
        clips_data = [
            {
                "title": "Ocean Waves",
                "description": "Relaxing ocean wave sounds for meditation",
                "genre": "ambient",
                "duration": "30s",
                "audio_url": "https://www2.cs.uic.edu/~i101/SoundFiles/BabyElephantWalk60.wav"
            },
            {
                "title": "Urban Beat",
                "description": "Modern electronic beat with urban vibes",
                "genre": "electronic",
                "duration": "45s", 
                "audio_url": "https://www2.cs.uic.edu/~i101/SoundFiles/CantinaBand60.wav"
            },
            {
                "title": "Acoustic Guitar",
                "description": "Gentle acoustic guitar melody",
                "genre": "acoustic",
                "duration": "60s",
                "audio_url": "https://www2.cs.uic.edu/~i101/SoundFiles/ImperialMarch60.wav"
            },
            {
                "title": "Rain Forest",
                "description": "Nature sounds from tropical rainforest",
                "genre": "ambient",
                "duration": "40s",
                "audio_url": "https://www2.cs.uic.edu/~i101/SoundFiles/PinkPanther60.wav"
            },
            {
                "title": "Synthwave Dream",
                "description": "Retro synthwave with dreamy atmosphere",
                "genre": "electronic",
                "duration": "55s",
                "audio_url": "https://www2.cs.uic.edu/~i101/SoundFiles/StarWars60.wav"
            },
            {
                "title": "Jazz Piano",
                "description": "Smooth jazz piano improvisation",
                "genre": "jazz",
                "duration": "35s",
                "audio_url": "https://www2.cs.uic.edu/~i101/SoundFiles/taunt.wav"
            }
        ]
        
        # Create clips in Supabase
        created_clips = []
        for clip_data in clips_data:
            clip_schema = schemas.ClipCreate(**clip_data)
            new_clip = crud.create_clip(db=db, clip=clip_schema)
            created_clips.append(new_clip.id)
        
        logger.info(f"✨ Seeded Supabase database with {len(created_clips)} clips on Vercel")
        
        return {
            "message": f"✅ Database seeded successfully with {len(created_clips)} clips!",
            "created_clip_ids": created_clips,
            "platform": "Vercel",
            "database": "Supabase",
            "next_step": "Test with GET /clips"
        }
        
    except Exception as e:
        logger.error(f"Database seeding failed: {e}")
        raise HTTPException(
            status_code=500, 
            detail=f"Database seeding failed: {str(e)}"
        )

# Get clips with enhanced error handling and rate limiting
@app.get("/clips", response_model=List[schemas.Clip])
@rate_limit(max_requests=50, window=300)
def get_clips(
    request: Request,  # Add request parameter for rate limiting
    skip: int = 0,
    limit: int = 100,
    genre: str = None,
    db: Session = Depends(get_db)
):
    """
    Get list of all available clips from Supabase
    
    - **skip**: Number of clips to skip (pagination)
    - **limit**: Maximum number of clips to return (max 100)
    - **genre**: Filter by genre (optional)
    """
    try:
        # Validate limit
        limit = min(limit, 100)
        
        clips = crud.get_clips(db, skip=skip, limit=limit)
        
        # Filter by genre if specified
        if genre:
            clips = [clip for clip in clips if clip.genre.lower() == genre.lower()]
        
        logger.info(f"📋 Retrieved {len(clips)} clips from Supabase via Vercel")
        return clips
        
    except Exception as e:
        logger.error(f"Failed to get clips from Supabase: {e}")
        raise HTTPException(
            status_code=500, 
            detail="Failed to retrieve clips from database"
        )

# Stream clip with enhanced logging and rate limiting
@app.get("/clips/{clip_id}/stream")
@rate_limit(max_requests=50, window=300)
def stream_clip(
    request: Request,  # Add request parameter for rate limiting
    clip_id: int, 
    db: Session = Depends(get_db)
):
    """
    Stream a clip and increment play count in Supabase
    
    - **clip_id**: The ID of the clip to stream
    """
    try:
        clip = crud.get_clip(db, clip_id=clip_id)
        if clip is None:
            logger.warning(f"🔍 Clip {clip_id} not found in Supabase")
            raise HTTPException(
                status_code=404, 
                detail=f"Clip with id {clip_id} not found"
            )
        
        # Increment play count in Supabase
        updated_clip = crud.increment_play_count(db, clip_id=clip_id)
        
        logger.info(f"🎵 Streaming clip {clip_id} via Vercel: '{clip.title}' (plays: {updated_clip.play_count})")
        
        # Return redirect to the actual audio URL for streaming
        return RedirectResponse(url=clip.audio_url, status_code=302)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to stream clip {clip_id}: {e}")
        raise HTTPException(
            status_code=500, 
            detail="Failed to stream clip"
        )

# Get clip stats with enhanced response and rate limiting
@app.get("/clips/{clip_id}/stats", response_model=schemas.ClipStats)
@rate_limit(max_requests=50, window=300)
def get_clip_stats(
    request: Request,  # Add request parameter for rate limiting
    clip_id: int, 
    db: Session = Depends(get_db)
):
    """
    Get clip statistics from Supabase including play count
    
    - **clip_id**: The ID of the clip
    """
    try:
        clip = crud.get_clip(db, clip_id=clip_id)
        if clip is None:
            logger.warning(f"🔍 Stats requested for non-existent clip {clip_id}")
            raise HTTPException(
                status_code=404, 
                detail=f"Clip with id {clip_id} not found"
            )
        
        stats = schemas.ClipStats(
            id=clip.id,
            title=clip.title,
            play_count=clip.play_count,
            description=clip.description,
            genre=clip.genre,
            duration=clip.duration
        )
        
        logger.info(f"📊 Stats retrieved for clip {clip_id}: {clip.play_count} plays")
        return stats
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get stats for clip {clip_id}: {e}")
        raise HTTPException(
            status_code=500, 
            detail="Failed to retrieve clip statistics"
        )

# Create clip with validation and rate limiting
@app.post("/clips", response_model=schemas.Clip)
@rate_limit(max_requests=10, window=300)  # Lower limit for creation
def create_clip(
    request: Request,  # Add request parameter for rate limiting
    clip: schemas.ClipCreate, 
    db: Session = Depends(get_db)
):
    """
    Create a new clip in Supabase (bonus feature)
    
    - **clip**: Clip data including title, description, genre, duration, and audio_url
    """
    try:
        # Validate audio URL is accessible (basic check)
        if not clip.audio_url.startswith(('http://', 'https://')):
            raise HTTPException(
                status_code=400,
                detail="Audio URL must be a valid HTTP/HTTPS URL"
            )
        
        # Validate duration format
        if not clip.duration.endswith('s'):
            raise HTTPException(
                status_code=400,
                detail="Duration must be in format like '30s', '45s', etc."
            )
        
        new_clip = crud.create_clip(db=db, clip=clip)
        logger.info(f"✨ Created new clip {new_clip.id} via Vercel: '{new_clip.title}' ({new_clip.genre})")
        return new_clip
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create clip in Supabase: {e}")
        raise HTTPException(
            status_code=500, 
            detail="Failed to create clip"
        )

# Bonus: Get popular clips
@app.get("/clips/popular", response_model=List[schemas.Clip])
@rate_limit(max_requests=50, window=300)
def get_popular_clips(
    request: Request,  # Add request parameter for rate limiting
    limit: int = 5, 
    db: Session = Depends(get_db)
):
    """
    Get most popular clips by play count from Supabase
    
    - **limit**: Number of popular clips to return (default: 5, max: 20)
    """
    try:
        # Validate limit
        limit = min(limit, 20)
        
        clips = crud.get_clips(db)
        # Sort by play count in descending order
        popular_clips = sorted(clips, key=lambda x: x.play_count, reverse=True)[:limit]
        
        logger.info(f"🔥 Retrieved {len(popular_clips)} popular clips from Supabase via Vercel")
        return popular_clips
        
    except Exception as e:
        logger.error(f"Failed to get popular clips: {e}")
        raise HTTPException(
            status_code=500, 
            detail="Failed to retrieve popular clips"
        )

# Bonus: Database stats endpoint
@app.get("/stats")
@rate_limit(max_requests=50, window=300)
def get_database_stats(
    request: Request,  # Add request parameter for rate limiting
    db: Session = Depends(get_db)
):
    """Get overall database statistics from Supabase"""
    try:
        clips = crud.get_clips(db)
        
        if not clips:
            return {
                "total_clips": 0,
                "total_plays": 0,
                "genres": [],
                "platform": "Vercel",
                "database": "Supabase"
            }
        
        total_plays = sum(clip.play_count for clip in clips)
        genres = list(set(clip.genre for clip in clips))
        most_popular = max(clips, key=lambda x: x.play_count)
        
        return {
            "total_clips": len(clips),
            "total_plays": total_plays,
            "genres": genres,
            "most_popular_clip": {
                "id": most_popular.id,
                "title": most_popular.title,
                "plays": most_popular.play_count
            },
            "platform": "Vercel Serverless",
            "database": "Supabase PostgreSQL",
            "region": os.getenv("VERCEL_REGION", "unknown"),
            "timestamp": time.time()
        }
        
    except Exception as e:
        logger.error(f"Failed to get database stats: {e}")
        raise HTTPException(
            status_code=500, 
            detail="Failed to retrieve database statistics"
        )