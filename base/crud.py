from sqlalchemy.orm import Session
from . import models, schemas

def get_clip(db: Session, clip_id: int):
    return db.query(models.Clip).filter(models.Clip.id == clip_id).first()

def get_clips(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Clip).offset(skip).limit(limit).all()

def create_clip(db: Session, clip: schemas.ClipCreate):
    db_clip = models.Clip(**clip.dict())
    db.add(db_clip)
    db.commit()
    db.refresh(db_clip)
    return db_clip

def increment_play_count(db: Session, clip_id: int):
    db_clip = db.query(models.Clip).filter(models.Clip.id == clip_id).first()
    if db_clip:
        db_clip.play_count += 1
        db.commit()
        db.refresh(db_clip)
    return db_clip