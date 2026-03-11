"""
Metadata extraction module for image and video files.
Extracts date/time, GPS coordinates, and device identifiers.
Uses exifread/PIL for images and pymediainfo for videos.
"""

import exifread
import re
from PIL import Image
from PIL.ExifTags import TAGS
from datetime import datetime
from typing import List, Optional, Tuple
from data_model import ExifData
from file_scanner import is_video_file
import os
import warnings
from pathlib import Path
from contextlib import redirect_stderr
from io import StringIO

try:
    from pymediainfo import MediaInfo
    PYMEDIAINFO_AVAILABLE = True
except ImportError:
    PYMEDIAINFO_AVAILABLE = False

try:
    from pillow_heif import register_heif_opener
    register_heif_opener()
except ImportError:
    pass

# Increase PIL image size limit to handle large images (we only read EXIF, not the full image)
Image.MAX_IMAGE_PIXELS = None  # Disable decompression bomb check
warnings.filterwarnings('ignore', category=Image.DecompressionBombWarning)


def _convert_to_decimal(degrees, minutes, seconds, ref):
    """
    Convert GPS coordinates from degrees/minutes/seconds to decimal.
    """
    decimal = float(degrees) + float(minutes) / 60.0 + float(seconds) / 3600.0
    if ref in ['S', 'W']:
        decimal = -decimal
    return decimal


def _get_gps_data(exif_data):
    """
    Extract GPS coordinates from EXIF data (PIL format).
    """
    if 'GPSInfo' not in exif_data:
        return None, None, None

    gps_info = exif_data['GPSInfo']
    lat = lon = alt = None

    if 2 in gps_info and 3 in gps_info:
        lat_deg, lat_min, lat_sec = gps_info[2][0], gps_info[2][1], gps_info[2][2]
        lat_ref = gps_info[3]
        lat = _convert_to_decimal(lat_deg, lat_min, lat_sec, lat_ref)

    if 4 in gps_info and 5 in gps_info:
        lon_deg, lon_min, lon_sec = gps_info[4][0], gps_info[4][1], gps_info[4][2]
        lon_ref = gps_info[5]
        lon = _convert_to_decimal(lon_deg, lon_min, lon_sec, lon_ref)

    if 6 in gps_info:
        alt = float(gps_info[6])

    return lat, lon, alt


def _parse_datetime(date_str: str) -> Optional[datetime]:
    """
    Parse EXIF datetime string to datetime object.
    """
    if not date_str or not isinstance(date_str, str):
        return None
    date_str = date_str.strip()
    if not date_str:
        return None

    try:
        return datetime.strptime(date_str, "%Y:%m:%d %H:%M:%S")
    except (ValueError, TypeError):
        pass

    try:
        from dateutil import parser as dateutil_parser
        return dateutil_parser.parse(date_str)
    except Exception:
        pass

    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%SZ"):
        try:
            return datetime.strptime(date_str.replace('Z', '').split('.')[0].strip(), fmt)
        except (ValueError, TypeError):
            continue
    return None


def _parse_iso6709(location_str: str) -> Tuple[Optional[float], Optional[float], Optional[float]]:
    """
    Parse an ISO 6709 location string into (latitude, longitude, altitude).
    Handles formats like "+34.0522-118.2437+100.000/" and "+34.0522-118.2437/".
    Also handles the compact DMS forms: +DDMM.MM-DDDMM.MM and +DDMMSS.SS-DDDMMSS.SS.
    """
    if not location_str or not isinstance(location_str, str):
        return None, None, None

    location_str = location_str.strip().rstrip('/')

    # Decimal degrees: +/-lat+/-lon optionally followed by +/-alt
    m = re.match(
        r'([+-]\d+(?:\.\d+)?)'   # latitude
        r'([+-]\d+(?:\.\d+)?)'   # longitude
        r'(?:([+-]\d+(?:\.\d+)?))?',  # optional altitude
        location_str
    )
    if not m:
        return None, None, None

    try:
        lat = float(m.group(1))
        lon = float(m.group(2))
        alt = float(m.group(3)) if m.group(3) else None
    except (ValueError, TypeError):
        return None, None, None

    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        return None, None, None

    return lat, lon, alt


def _extract_video_metadata(file_path: str) -> ExifData:
    """
    Extract metadata from a video file using pymediainfo.
    Extracts date/time, GPS coordinates, and device identifiers.
    """
    file_name = os.path.basename(file_path)
    exif_data = ExifData(file_path=file_path, file_name=file_name)

    if not PYMEDIAINFO_AVAILABLE:
        return exif_data

    try:
        media_info = MediaInfo.parse(file_path)
    except Exception:
        return exif_data

    general_data = {}
    for track in media_info.tracks:
        if track.track_type == "General":
            general_data = track.to_data()
            break

    # --- Date/time ---
    for date_key in ('recorded_date', 'encoded_date', 'tagged_date',
                     'mastered_date', 'file_last_modification_date'):
        raw = general_data.get(date_key)
        if raw:
            date_str = str(raw)
            # MediaInfo often prefixes dates with "UTC " -- strip it for parsing
            if date_str.upper().startswith('UTC '):
                date_str = date_str[4:]
            parsed = _parse_datetime(date_str)
            if parsed:
                exif_data.date_taken = parsed
                break

    # --- GPS from ISO 6709 location fields ---
    location_raw = None
    for loc_key in ('xyz', 'comapplequicktimelocationiso6709',
                    'com_apple_quicktime_location_iso6709',
                    'location'):
        val = general_data.get(loc_key)
        if val:
            location_raw = str(val)
            break

    # Fallback: scan all keys for anything containing "location" or "gps"
    if not location_raw:
        for key, val in general_data.items():
            if val and any(kw in key.lower() for kw in ('location', 'gps', 'xyz', 'iso6709')):
                candidate = str(val)
                if re.search(r'[+-]\d', candidate):
                    location_raw = candidate
                    break

    if location_raw:
        lat, lon, alt = _parse_iso6709(location_raw)
        if lat is not None:
            exif_data.latitude = lat
        if lon is not None:
            exif_data.longitude = lon
        if alt is not None:
            exif_data.altitude = alt

    # --- Make / Model ---
    for make_key in ('comapplequicktimemake', 'com_apple_quicktime_make',
                     'make', 'performer'):
        val = general_data.get(make_key)
        if val:
            exif_data.make = str(val).strip()
            break

    for model_key in ('comapplequicktimemodel', 'com_apple_quicktime_model',
                      'model', 'camera_model_name'):
        val = general_data.get(model_key)
        if val:
            exif_data.model = str(val).strip()
            break

    # --- Serial number ---
    for serial_key in ('comapplequicktimecreationdate', 'serial_number',
                       'comapplequicktimeserialnumber'):
        val = general_data.get(serial_key)
        if val and serial_key != 'comapplequicktimecreationdate':
            exif_data.serial_number = str(val).strip()
            break

    # --- Software / writing application ---
    for sw_key in ('writing_application', 'encoding_settings',
                   'comapplequicktimesoftware', 'com_apple_quicktime_software',
                   'encoded_library_name'):
        val = general_data.get(sw_key)
        if val:
            exif_data.software = str(val).strip()
            break

    return exif_data


def _get_all_video_tags(file_path: str) -> List[Tuple[str, str]]:
    """
    Read all metadata tags from a video file using pymediainfo.
    Returns a sorted list of (tag_name, value_str).
    """
    if not PYMEDIAINFO_AVAILABLE:
        return []

    try:
        media_info = MediaInfo.parse(file_path)
    except Exception:
        return []

    result: List[Tuple[str, str]] = []
    for track in media_info.tracks:
        track_type = track.track_type or "Unknown"
        data = track.to_data()
        for key, value in sorted(data.items()):
            if value is None or str(value).strip() == '':
                continue
            tag_name = f"[{track_type}] {key}"
            val_str = str(value).strip()
            # Truncate very long values to keep the dialog readable
            if len(val_str) > 500:
                val_str = val_str[:500] + "..."
            result.append((tag_name, val_str))

    return sorted(result, key=lambda x: x[0])


# Tag keys that contain binary data; show a short summary instead of raw bytes
_BINARY_TAGS = frozenset({
    'JPEGThumbnail', 'TIFFThumbnail', 'EXIF MakerNote', 'EXIF Makernote',
    'InteroperabilityTag', 'Image Tag 0x927C', 'Image Tag 0x9C9B', 'Image Tag 0x9C9C',
})


def get_all_exif_tags(file_path: str) -> List[Tuple[str, str]]:
    """
    Read all EXIF/metadata tags from a media file for display.
    Routes to pymediainfo for video files and exifread/PIL for images.
    Returns a sorted list of (tag_name, value_str). Binary tags are summarized as "(binary, N bytes)".
    On error returns an empty list.
    """
    if is_video_file(file_path):
        return _get_all_video_tags(file_path)

    result: List[Tuple[str, str]] = []
    seen: set = set()

    def add_tag(name: str, value_str: str) -> None:
        if name in seen:
            return
        seen.add(name)
        result.append((name, value_str))

    try:
        with open(file_path, 'rb') as f:
            tags = exifread.process_file(f)
    except (OSError, IOError, ValueError):
        return []

    for tag_name, value in tags.items():
        if tag_name in _BINARY_TAGS or isinstance(value, (bytes, bytearray)):
            try:
                size = len(value)
            except (TypeError, AttributeError):
                size = 0
            add_tag(tag_name, f"(binary, {size} bytes)")
        else:
            try:
                add_tag(tag_name, str(value).strip())
            except Exception:
                add_tag(tag_name, "(unable to convert)")

    if not result:
        try:
            with warnings.catch_warnings():
                warnings.filterwarnings('ignore')
                with redirect_stderr(StringIO()):
                    with Image.open(file_path) as img:
                        if hasattr(img, '_getexif') and img._getexif() is not None:
                            for tag_id, value in img._getexif().items():
                                name = TAGS.get(tag_id, f"Tag {tag_id}")
                                if name in seen:
                                    continue
                                seen.add(name)
                                try:
                                    result.append((name, str(value).strip()))
                                except Exception:
                                    result.append((name, "(unable to convert)"))
        except Exception:
            pass

    return sorted(result, key=lambda x: x[0])


def extract_exif_data(file_path: str) -> ExifData:
    """
    Extract metadata from a media file (image or video).
    Only extracts date/time, GPS coordinates, and device identifiers.
    """
    if is_video_file(file_path):
        return _extract_video_metadata(file_path)

    file_name = os.path.basename(file_path)
    exif_data = ExifData(file_path=file_path, file_name=file_name)

    try:
        stderr_capture = StringIO()
        with redirect_stderr(stderr_capture):
            with open(file_path, 'rb') as f:
                tags = exifread.process_file(f, details=False)

            for date_tag in ['EXIF DateTimeOriginal', 'Image DateTime', 'EXIF DateTimeDigitized']:
                if date_tag in tags:
                    date_str = str(tags[date_tag])
                    exif_data.date_taken = _parse_datetime(date_str)
                    if exif_data.date_taken:
                        break

            if 'Image Make' in tags:
                exif_data.make = str(tags['Image Make']).strip()
            if 'Image Model' in tags:
                exif_data.model = str(tags['Image Model']).strip()
            if 'EXIF BodySerialNumber' in tags:
                exif_data.serial_number = str(tags['EXIF BodySerialNumber']).strip()
            elif 'Image SerialNumber' in tags:
                exif_data.serial_number = str(tags['Image SerialNumber']).strip()
            if 'Image Software' in tags:
                exif_data.software = str(tags['Image Software']).strip()

            if 'GPS GPSLatitude' in tags and 'GPS GPSLatitudeRef' in tags:
                lat_deg = tags['GPS GPSLatitude'].values[0]
                lat_min = tags['GPS GPSLatitude'].values[1]
                lat_sec = tags['GPS GPSLatitude'].values[2]
                lat_ref = str(tags['GPS GPSLatitudeRef'])
                exif_data.latitude = _convert_to_decimal(lat_deg, lat_min, lat_sec, lat_ref)

            if 'GPS GPSLongitude' in tags and 'GPS GPSLongitudeRef' in tags:
                lon_deg = tags['GPS GPSLongitude'].values[0]
                lon_min = tags['GPS GPSLongitude'].values[1]
                lon_sec = tags['GPS GPSLongitude'].values[2]
                lon_ref = str(tags['GPS GPSLongitudeRef'])
                exif_data.longitude = _convert_to_decimal(lon_deg, lon_min, lon_sec, lon_ref)

            if 'GPS GPSAltitude' in tags:
                alt = tags['GPS GPSAltitude']
                exif_data.altitude = float(alt.values[0])
                if 'GPS GPSAltitudeRef' in tags and str(tags['GPS GPSAltitudeRef']) == '1':
                    exif_data.altitude = -exif_data.altitude

        if not exif_data.has_gps():
            try:
                with warnings.catch_warnings():
                    warnings.filterwarnings('ignore')
                    try:
                        with redirect_stderr(StringIO()):
                            with Image.open(file_path) as img:
                                if hasattr(img, '_getexif') and img._getexif() is not None:
                                    exif_dict = img._getexif()
                                    lat, lon, alt = _get_gps_data(exif_dict)
                                    if lat is not None:
                                        exif_data.latitude = lat
                                    if lon is not None:
                                        exif_data.longitude = lon
                                    if alt is not None:
                                        exif_data.altitude = alt
                                    if exif_data.date_taken is None:
                                        for tag_id, value in exif_dict.items():
                                            tag = TAGS.get(tag_id, tag_id)
                                            if tag in ['DateTime', 'DateTimeOriginal', 'DateTimeDigitized']:
                                                exif_data.date_taken = _parse_datetime(str(value))
                                                if exif_data.date_taken:
                                                    break
                                    if not exif_data.make:
                                        for tag_id, value in exif_dict.items():
                                            tag = TAGS.get(tag_id, tag_id)
                                            if tag == 'Make':
                                                exif_data.make = str(value).strip()
                                            elif tag == 'Model':
                                                exif_data.model = str(value).strip()
                                            elif tag == 'Software':
                                                exif_data.software = str(value).strip()
                    except (Exception, IOError, OSError):
                        pass
            except Exception:
                pass

    except Exception:
        pass

    return exif_data
