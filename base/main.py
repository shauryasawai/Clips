from collections import defaultdict
from functools import wraps
from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
# Remove Prometheus for Vercel serverless
# from prometheus_fastapi_instrumentator import Instrumentator
import time
import logging
from typing import List
import os

from . import crud, models, schemas
from .database import SessionLocal, engine
from .config import settings

# Create database tables (important for serverless)
models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Clips API",
    description="Backend service for streaming audio clips with Supabase database - Deployed on Vercel",
    version="1.0.0",
    # Conditional docs for production
    docs_url="/docs" if settings.environment != "production" else None,
    redoc_url="/redoc" if settings.environment != "production" else None
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://your-frontend-domain.com",
        "https://*.vercel.app",  # Your Vercel deployments
        "http://localhost:3000"  # Local development only
    ] if settings.environment == "production" else ["*"],
    allow_credentials=False,  
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Content-Type", "Authorization"],
    max_age=600  
)

# Remove Prometheus for serverless - Vercel has built-in analytics
# instrumentator = Instrumentator()
# instrumentator.instrument(app).expose(app)

# Database dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Simplified logging for serverless
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Vercel serverless startup - no persistent state
@app.on_event("startup")
async def startup_event():
    """Validate database connection on serverless startup"""
    try:
        db = SessionLocal()
        # Quick connection test to Supabase
        result = db.execute("SELECT 1")
        result.fetchone()
        db.close()
        
        logger.info("🚀 Clips API starting on Vercel...")
        logger.info(f"🔧 Environment: {settings.environment}")
        logger.info(f"🗄️ Database: Supabase PostgreSQL")
        logger.info("✅ Serverless startup completed!")
        
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        # Don't raise exception - let it continue for better UX
        logger.error("⚠️ Continuing without database validation...")

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
        "endpoints": {
            "documentation": "/docs" if settings.environment != "production" else "Not available in production",
            "health": "/health",
            "clips": "/clips",
            "stream": "/clips/{id}/stream",
            "stats": "/clips/{id}/stats",
            "init": "/admin/init-db"
        }
    }

# Enhanced health check with Vercel info
@app.get("/health")
def health_check(db: Session = Depends(get_db)):
    """Comprehensive health check including Supabase connectivity"""
    try:
        # Test Supabase connection
        db.execute("SELECT 1")
        
        # Get basic stats from Supabase
        clip_count = db.query(models.Clip).count()
        total_plays = db.query(models.Clip).with_entities(models.Clip.play_count).all()
        total_play_count = sum([play[0] for play in total_plays]) if total_plays else 0
        
        return {
            "status": "healthy",
            "timestamp": time.time(),
            "platform": "Vercel Serverless",
            "region": os.getenv("VERCEL_REGION", "unknown"),
            "database": {
                "provider": "Supabase",
                "status": "connected",
                "host": settings.database_url.split('@')[1].split('/')[0] if '@' in settings.database_url else "localhost"
            },
            "stats": {
                "total_clips": clip_count,
                "total_plays": total_play_count
            },
            "environment": settings.environment
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
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

# Vercel database initialization endpoint
@app.post("/admin/init-db")
def init_database(db: Session = Depends(get_db)):
    """Initialize Supabase database with sample data (run once after deployment)"""
    try:
        # Check if data already exists
        existing_clips = crud.get_clips(db, limit=1)
        if existing_clips:
            return {
                "message": "Database already initialized",
                "existing_clips": len(crud.get_clips(db)),
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
        
        logger.info(f"✨ Initialized Supabase database with {len(created_clips)} clips on Vercel")
        
        return {
            "message": f"Database initialized successfully with {len(created_clips)} clips!",
            "created_clip_ids": created_clips,
            "platform": "Vercel",
            "database": "Supabase"
        }
        
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise HTTPException(
            status_code=500, 
            detail=f"Database initialization failed: {str(e)}"
        )

# Get clips with enhanced error handling
@app.get("/clips", response_model=List[schemas.Clip])
@rate_limit(max_requests=50, window=300)
def get_clips(
    skip: int = 0,
    limit: int = 100,
    genre: str = None,
    db: Session = Depends(get_db)
):
    """
    Get list of all available clips from Supabase
    
    - **skip**: Number of clips to skip (pagination)
    - **limit**: Maximum number of clips to return
    - **genre**: Filter by genre (optional)
    """
    try:
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

# Stream clip with enhanced logging
@app.get("/clips/{clip_id}/stream")
@rate_limit(max_requests=50, window=300)
def stream_clip(clip_id: int, db: Session = Depends(get_db)):
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

# Get clip stats with enhanced response
@app.get("/clips/{clip_id}/stats", response_model=schemas.ClipStats)
@rate_limit(max_requests=50, window=300)
def get_clip_stats(clip_id: int, db: Session = Depends(get_db)):
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

# Create clip with validation
@app.post("/clips", response_model=schemas.Clip)
@rate_limit(max_requests=50, window=300)
def create_clip(clip: schemas.ClipCreate, db: Session = Depends(get_db)):
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
def get_popular_clips(limit: int = 5, db: Session = Depends(get_db)):
    """
    Get most popular clips by play count from Supabase
    
    - **limit**: Number of popular clips to return (default: 5)
    """
    try:
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
def get_database_stats(db: Session = Depends(get_db)):
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