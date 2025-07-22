import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.orm import Session
from base.database import SessionLocal, engine
from base import models
from base.config import settings

def seed_database():
    print(f"🌱 Seeding database at: {settings.database_url.split('@')[1] if '@' in settings.database_url else 'localhost'}")
    
    # Create tables
    models.Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    
    try:
        # Check if data already exists
        if db.query(models.Clip).count() > 0:
            print("✅ Database already has data!")
            return
        
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
        
        # Create clips
        for clip_data in clips_data:
            clip = models.Clip(**clip_data)
            db.add(clip)
        
        db.commit()
        print(f"✅ Database seeded with {len(clips_data)} clips!")
        
    except Exception as e:
        print(f"❌ Error seeding database: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    seed_database()