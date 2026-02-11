"""
Map viewing utilities for opening GPS locations in a browser.
"""

import webbrowser
from typing import Optional


def open_location_in_map(latitude: float, longitude: float, service: str = 'google') -> bool:
    """
    Open GPS location in a web browser using a mapping service.
    
    Args:
        latitude: Latitude coordinate
        longitude: Longitude coordinate
        service: Mapping service to use ('google' or 'osm' for OpenStreetMap)
    
    Returns:
        True if successful, False otherwise
    """
    if latitude is None or longitude is None:
        return False
    
    try:
        if service.lower() == 'osm':
            # OpenStreetMap
            url = f"https://www.openstreetmap.org/?mlat={latitude}&mlon={longitude}&zoom=15"
        else:
            # Google Maps (default)
            url = f"https://www.google.com/maps?q={latitude},{longitude}"
        
        webbrowser.open(url)
        return True
    except Exception:
        return False

