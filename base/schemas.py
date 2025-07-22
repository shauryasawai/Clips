from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class ClipBase(BaseModel):
    title: str
    description: Optional[str] = None
    genre: str
    duration: str
    audio_url: str

class ClipCreate(ClipBase):
    pass

class Clip(ClipBase):
    id: int
    play_count: int
    created_at: datetime

    class Config:
        from_attributes = True

class ClipStats(BaseModel):
    id: int
    title: str
    play_count: int
    description: Optional[str]
    genre: str
    duration: str