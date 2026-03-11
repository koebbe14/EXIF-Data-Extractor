"""
Thumbnail generation utilities for image and video files.
"""

from contextlib import redirect_stderr
from io import StringIO
from PIL import Image
from pathlib import Path
from typing import Optional

from file_scanner import IMAGE_EXTENSIONS, VIDEO_EXTENSIONS

try:
    from pillow_heif import register_heif_opener
    register_heif_opener()
except ImportError:
    pass

try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False

THUMBNAIL_SIZE = (150, 150)


def _create_image_thumbnail(file_path: str, size: tuple) -> Optional[Image.Image]:
    """Create a thumbnail from an image file."""
    try:
        with redirect_stderr(StringIO()):
            with Image.open(file_path) as img:
                if img.mode in ('RGBA', 'LA', 'P'):
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    if img.mode == 'P':
                        img = img.convert('RGBA')
                    background.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
                    img = background
                elif img.mode != 'RGB':
                    img = img.convert('RGB')

                img.thumbnail(size, Image.Resampling.LANCZOS)
                thumb = img.copy()
        if getattr(thumb, 'info', None) and 'icc_profile' in thumb.info:
            thumb.info.pop('icc_profile', None)
        return thumb
    except Exception:
        return None


def _create_video_thumbnail(file_path: str, size: tuple) -> Optional[Image.Image]:
    """Extract a frame from a video file and return it as a PIL thumbnail."""
    if not CV2_AVAILABLE:
        return None

    cap = None
    try:
        cap = cv2.VideoCapture(file_path)
        if not cap.isOpened():
            return None

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0

        # Seek to 1 second in, or 10% through, whichever is smaller
        target_frame = min(int(fps), max(1, total_frames // 10))
        cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)

        ret, frame = cap.read()
        if not ret:
            # Fall back to the very first frame
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ret, frame = cap.read()
        if not ret:
            return None

        # OpenCV uses BGR; convert to RGB for PIL
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(frame_rgb)
        img.thumbnail(size, Image.Resampling.LANCZOS)
        return img
    except Exception:
        return None
    finally:
        if cap is not None:
            cap.release()


def create_thumbnail(file_path: str, size: tuple = THUMBNAIL_SIZE) -> Optional[Image.Image]:
    """
    Create a thumbnail from an image or video file.
    For images: opens with PIL and resizes.
    For videos: extracts a frame with OpenCV and resizes.
    """
    file_ext = Path(file_path).suffix.lower()

    if file_ext in IMAGE_EXTENSIONS:
        return _create_image_thumbnail(file_path, size)
    elif file_ext in VIDEO_EXTENSIONS:
        return _create_video_thumbnail(file_path, size)

    return None
