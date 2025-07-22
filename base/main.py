from collections import defaultdict
from functools import wraps
from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.responses import RedirectResponse, JSONResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import create_engine, text
import time
import logging
from typing import List
import os
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST

from . import crud, models, schemas
from .database import SessionLocal, engine
from .config import settings

app = FastAPI(
    title="Clips API",
    description="Backend service for streaming audio clips with Supabase database",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    max_age=600
)

# Prometheus Metrics
HTTP_REQUESTS = Counter('http_requests_total', 'Total HTTP requests', ['method', 'endpoint', 'status'])
REQUEST_DURATION = Histogram('http_request_duration_seconds', 'Request duration', ['method', 'endpoint'])
CLIPS_STREAMED = Counter('clips_streamed_total', 'Total clips streamed', ['clip_id', 'title', 'genre'])
ACTIVE_CLIPS = Gauge('clips_total', 'Total clips in database')
TOTAL_PLAYS = Gauge('clips_total_plays', 'Total plays across all clips')
DB_OPERATIONS = Counter('database_operations_total', 'Database operations', ['operation'])

# Database dependency
def get_db():
    db = None
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        yield db
    except Exception as e:
        logging.error(f"Database error: {e}")
        if db:
            db.rollback()
        raise HTTPException(status_code=503, detail="Database connection failed")
    finally:
        if db:
            db.close()

# Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Rate limiting
request_counts = defaultdict(list)

def rate_limit(max_requests: int = 100, window: int = 300):
    def decorator(func):
        @wraps(func)
        def wrapper(request: Request, *args, **kwargs):
            client_ip = request.client.host if request.client else "unknown"
            now = time.time()
            
            request_counts[client_ip] = [t for t in request_counts[client_ip] if now - t < window]
            
            if len(request_counts[client_ip]) >= max_requests:
                raise HTTPException(status_code=429, detail="Rate limit exceeded")
            
            request_counts[client_ip].append(now)
            return func(request, *args, **kwargs)
        return wrapper
    return decorator

# Metrics middleware
@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    start_time = time.time()
    
    try:
        response = await call_next(request)
        process_time = time.time() - start_time
        
        # Record metrics
        HTTP_REQUESTS.labels(
            method=request.method,
            endpoint=request.url.path,
            status=str(response.status_code)
        ).inc()
        
        REQUEST_DURATION.labels(
            method=request.method,
            endpoint=request.url.path
        ).observe(process_time)
        
        # Logging
        status_emoji = "✅" if response.status_code < 400 else "❌"
        logger.info(f"{status_emoji} {request.method} {request.url.path} - {response.status_code} - {process_time:.3f}s")
        
        # Headers
        response.headers["X-Process-Time"] = str(process_time)
        response.headers["X-Platform"] = "Vercel"
        response.headers["X-Database"] = "Supabase"
        
        return response
        
    except Exception as e:
        process_time = time.time() - start_time
        logger.error(f"💥 {request.method} {request.url.path} - ERROR: {e} - {process_time:.3f}s")
        
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error", "message": str(e), "timestamp": time.time()}
        )

# Root endpoint
@app.get("/")
async def root():
    return {
        "message": "🎵 Clips API - Audio streaming service",
        "version": "1.0.0",
        "platform": "Vercel Serverless",
        "database": "Supabase PostgreSQL",
        "status": "online",
        "endpoints": {
            "docs": "/docs",
            "health": "/health", 
            "metrics": "/metrics",
            "setup": "/admin/setup-db",
            "seed": "/admin/seed-db",
            "clips": "/clips",
            "stream": "/clips/{id}/stream",
            "stats": "/clips/{id}/stats"
        }
    }

# Metrics endpoint
@app.get("/metrics")
def get_metrics():
    """Prometheus metrics endpoint"""
    try:
        # Update gauges with fresh data
        db = SessionLocal()
        clips = crud.get_clips(db)
        ACTIVE_CLIPS.set(len(clips))
        TOTAL_PLAYS.set(sum(clip.play_count for clip in clips) if clips else 0)
        db.close()
    except:
        pass  # Don't fail metrics if DB is down
    
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

# Health check
@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "platform": "Vercel Serverless",
        "region": os.getenv("VERCEL_REGION", "unknown")
    }

# Debug database
@app.get("/debug/database")
def debug_database():
    try:
        test_engine = create_engine(
            settings.database_url,
            pool_size=1,
            connect_args={"connect_timeout": 30, "sslmode": "require"}
        )
        
        with test_engine.connect() as conn:
            version = conn.execute(text("SELECT version()")).fetchone()
            table_check = conn.execute(text("""
                SELECT COUNT(*) FROM information_schema.tables 
                WHERE table_name = 'clips' AND table_schema = 'public'
            """)).fetchone()[0]
            
            clip_count = 0
            if table_check > 0:
                clip_count = conn.execute(text("SELECT COUNT(*) FROM clips")).fetchone()[0]
            
        return {
            "status": "✅ CONNECTION SUCCESS",
            "version": version[0][:50],
            "clips_table_exists": table_check > 0,
            "clips_count": clip_count
        }
        
    except Exception as e:
        return {
            "status": "❌ CONNECTION FAILED",
            "error": str(e),
            "suggestion": "Check Supabase project status and connection string"
        }

# Setup database
@app.post("/admin/setup-db")
def setup_database():
    try:
        models.Base.metadata.create_all(bind=engine)
        
        with engine.connect() as conn:
            table_exists = conn.execute(text("""
                SELECT COUNT(*) FROM information_schema.tables 
                WHERE table_name = 'clips'
            """)).fetchone()[0] > 0
            
            if not table_exists:
                raise Exception("Table creation failed")
                
        DB_OPERATIONS.labels(operation="CREATE_TABLES").inc()
        
        return {
            "message": "✅ Database tables created successfully!",
            "next_step": "Run POST /admin/seed-db"
        }
        
    except Exception as e:
        logger.error(f"Setup failed: {e}")
        raise HTTPException(status_code=500, detail=f"Setup failed: {e}")

# Seed database
@app.post("/admin/seed-db")
def seed_database(db: Session = Depends(get_db)):
    try:
        existing = db.query(models.Clip).count()
        if existing > 0:
            return {"message": "Database already has data", "existing_clips": existing}
        
        clips_data = [
            {"title": "Ocean Waves", "description": "Relaxing waves", "genre": "ambient", "duration": "30s", 
             "audio_url": "https://www2.cs.uic.edu/~i101/SoundFiles/BabyElephantWalk60.wav"},
            {"title": "Urban Beat", "description": "Electronic beat", "genre": "electronic", "duration": "45s",
             "audio_url": "https://www2.cs.uic.edu/~i101/SoundFiles/CantinaBand60.wav"},
            {"title": "Acoustic Guitar", "description": "Guitar melody", "genre": "acoustic", "duration": "60s",
             "audio_url": "https://www2.cs.uic.edu/~i101/SoundFiles/ImperialMarch60.wav"},
            {"title": "Rain Forest", "description": "Nature sounds", "genre": "ambient", "duration": "40s",
             "audio_url": "https://www2.cs.uic.edu/~i101/SoundFiles/PinkPanther60.wav"},
            {"title": "Synthwave Dream", "description": "Retro synthwave", "genre": "electronic", "duration": "55s",
             "audio_url": "https://www2.cs.uic.edu/~i101/SoundFiles/StarWars60.wav"},
            {"title": "Jazz Piano", "description": "Jazz improvisation", "genre": "jazz", "duration": "35s",
             "audio_url": "https://www2.cs.uic.edu/~i101/SoundFiles/taunt.wav"}
        ]
        
        created_clips = []
        for clip_data in clips_data:
            clip = crud.create_clip(db, schemas.ClipCreate(**clip_data))
            created_clips.append(clip.id)
        
        DB_OPERATIONS.labels(operation="INSERT").inc()
        ACTIVE_CLIPS.set(len(created_clips))
        
        return {
            "message": f"✅ Database seeded with {len(created_clips)} clips!",
            "created_clip_ids": created_clips
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Seeding failed: {e}")

# Get clips
@app.get("/clips", response_model=List[schemas.Clip])
@rate_limit(max_requests=50, window=300)
def get_clips(request: Request, skip: int = 0, limit: int = 100, genre: str = None, db: Session = Depends(get_db)):
    try:
        DB_OPERATIONS.labels(operation="SELECT").inc()
        limit = min(limit, 100)
        clips = crud.get_clips(db, skip=skip, limit=limit)
        
        if genre:
            clips = [c for c in clips if c.genre.lower() == genre.lower()]
        
        return clips
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to retrieve clips")

# Stream clip
@app.get("/clips/{clip_id}/stream")
@rate_limit(max_requests=50, window=300)
def stream_clip(request: Request, clip_id: int, db: Session = Depends(get_db)):
    try:
        DB_OPERATIONS.labels(operation="SELECT").inc()
        clip = crud.get_clip(db, clip_id=clip_id)
        if not clip:
            raise HTTPException(status_code=404, detail="Clip not found")
        
        DB_OPERATIONS.labels(operation="UPDATE").inc()
        updated_clip = crud.increment_play_count(db, clip_id=clip_id)
        
        # Record stream metrics
        CLIPS_STREAMED.labels(
            clip_id=str(clip_id),
            title=clip.title,
            genre=clip.genre
        ).inc()
        
        # Update total plays
        total_plays = db.query(models.Clip).with_entities(models.Clip.play_count).all()
        TOTAL_PLAYS.set(sum(play[0] for play in total_plays) if total_plays else 0)
        
        return RedirectResponse(url=clip.audio_url, status_code=302)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to stream clip")

# Get clip stats
@app.get("/clips/{clip_id}/stats", response_model=schemas.ClipStats)
@rate_limit(max_requests=50, window=300)
def get_clip_stats(request: Request, clip_id: int, db: Session = Depends(get_db)):
    try:
        DB_OPERATIONS.labels(operation="SELECT").inc()
        clip = crud.get_clip(db, clip_id=clip_id)
        if not clip:
            raise HTTPException(status_code=404, detail="Clip not found")
        
        return schemas.ClipStats(
            id=clip.id, title=clip.title, play_count=clip.play_count,
            description=clip.description, genre=clip.genre, duration=clip.duration
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to get stats")

# Create clip
@app.post("/clips", response_model=schemas.Clip)
@rate_limit(max_requests=10, window=300)
def create_clip(request: Request, clip: schemas.ClipCreate, db: Session = Depends(get_db)):
    try:
        if not clip.audio_url.startswith(('http://', 'https://')):
            raise HTTPException(status_code=400, detail="Invalid audio URL")
        
        if not clip.duration.endswith('s'):
            raise HTTPException(status_code=400, detail="Duration must end with 's'")
        
        DB_OPERATIONS.labels(operation="INSERT").inc()
        new_clip = crud.create_clip(db, clip)
        
        # Update gauge
        total_clips = db.query(models.Clip).count()
        ACTIVE_CLIPS.set(total_clips)
        
        return new_clip
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to create clip")

# Popular clips
@app.get("/clips/popular", response_model=List[schemas.Clip])
@rate_limit(max_requests=50, window=300)
def get_popular_clips(request: Request, limit: int = 5, db: Session = Depends(get_db)):
    try:
        DB_OPERATIONS.labels(operation="SELECT").inc()
        limit = min(limit, 20)
        clips = crud.get_clips(db)
        popular = sorted(clips, key=lambda x: x.play_count, reverse=True)[:limit]
        return popular
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to get popular clips")

# Database stats
@app.get("/stats")
@rate_limit(max_requests=50, window=300)
def get_database_stats(request: Request, db: Session = Depends(get_db)):
    try:
        DB_OPERATIONS.labels(operation="SELECT").inc()
        clips = crud.get_clips(db)
        
        if not clips:
            return {"total_clips": 0, "total_plays": 0, "genres": [], "platform": "Vercel"}
        
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
            "timestamp": time.time()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to get stats")