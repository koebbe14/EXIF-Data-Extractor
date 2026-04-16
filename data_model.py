"""
Data model for storing EXIF information extracted from images.
Only includes date/time, GPS coordinates, and device identifiers.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Any
from datetime import datetime


@dataclass
class ExifData:
    """Data structure to hold extracted EXIF information."""
    
    file_path: str
    file_name: str
    date_taken: Optional[datetime] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    altitude: Optional[float] = None
    make: Optional[str] = None
    model: Optional[str] = None
    serial_number: Optional[str] = None
    software: Optional[str] = None
    thumbnail: Optional[Any] = None  # PIL Image object for thumbnail
    # Lazy cache used for "include full metadata" search. Filled on demand.
    full_metadata_search_text: Optional[str] = None

    def has_gps(self) -> bool:
        """Check if GPS coordinates are available."""
        return self.latitude is not None and self.longitude is not None

    @property
    def extension(self) -> str:
        try:
            return Path(self.file_name or self.file_path).suffix.lower()
        except Exception:
            return ""

    @property
    def is_video(self) -> bool:
        ext = self.extension
        return ext in {
            '.mp4', '.m4v', '.mov', '.avi', '.mkv',
            '.wmv', '.asf', '.flv', '.webm',
            '.3gp', '.3g2', '.mts', '.m2ts', '.ts',
            '.vob', '.mpg', '.mpeg', '.ogv',
        }
    
    def to_dict(self) -> dict:
        """Convert to dictionary for export."""
        return {
            'file_path': self.file_path,
            'file_name': self.file_name,
            'date_taken': self.date_taken.isoformat() if self.date_taken else None,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'altitude': self.altitude,
            'make': self.make,
            'model': self.model,
            'serial_number': self.serial_number,
            'software': self.software
        }

