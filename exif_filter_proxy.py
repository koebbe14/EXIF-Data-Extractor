from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Set, Tuple

from PyQt5.QtCore import QSortFilterProxyModel, QModelIndex, Qt

from data_model import ExifData
from exif_extractor import get_all_exif_tags


def _tokenize(text: str) -> Set[str]:
    return {t for t in re.split(r"[^0-9A-Za-z_.+-]+", text.casefold()) if t}


def _try_parse_latlon(query: str) -> Optional[Tuple[Optional[float], Optional[float]]]:
    q = query.strip()
    if not q:
        return None
    if "," in q:
        parts = [p.strip() for p in q.split(",") if p.strip()]
        if len(parts) == 2:
            try:
                return float(parts[0]), float(parts[1])
            except ValueError:
                return None
        return None
    try:
        return float(q), None
    except ValueError:
        return None


@dataclass
class ExifProxyFilters:
    query: str = ""
    partial_match: bool = True
    include_full_metadata: bool = False

    file_type: str = "All"  # All|Images|Videos
    extensions: Set[str] = None  # e.g. {'.jpg', '.mp4'}
    gps: str = "Any"  # Any|Has GPS|Missing GPS
    serial_presence: str = "Any"  # Any|Present|Missing

    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None

    makes: Set[str] = None
    models: Set[str] = None
    softwares: Set[str] = None

    def __post_init__(self):
        self.extensions = set() if self.extensions is None else set(self.extensions)
        self.makes = set() if self.makes is None else set(self.makes)
        self.models = set() if self.models is None else set(self.models)
        self.softwares = set() if self.softwares is None else set(self.softwares)


class ExifFilterProxy(QSortFilterProxyModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._f = ExifProxyFilters()
        self.setFilterCaseSensitivity(Qt.CaseInsensitive)
        self.setDynamicSortFilter(True)

    def set_filters(self, filters: ExifProxyFilters) -> None:
        self._f = filters
        self.invalidateFilter()

    def filters(self) -> ExifProxyFilters:
        return self._f

    def lessThan(self, left: QModelIndex, right: QModelIndex) -> bool:
        l = self.sourceModel().data(left, Qt.UserRole)
        r = self.sourceModel().data(right, Qt.UserRole)

        if l is None and r is None:
            return False
        if l is None:
            return True
        if r is None:
            return False
        try:
            return l < r
        except Exception:
            return str(l) < str(r)

    def _source_row(self, source_row: int) -> Optional[ExifData]:
        model = self.sourceModel()
        if model is None:
            return None
        getter = getattr(model, "get_row", None)
        if callable(getter):
            return getter(source_row)
        return None

    def _build_row_search_text(self, exif: ExifData) -> str:
        core = " ".join(
            [
                exif.file_name or "",
                exif.file_path or "",
                (exif.make or ""),
                (exif.model or ""),
                (exif.serial_number or ""),
                (exif.software or ""),
                f"{exif.latitude:.6f}" if exif.latitude is not None else "",
                f"{exif.longitude:.6f}" if exif.longitude is not None else "",
                f"{exif.altitude:.2f}" if exif.altitude is not None else "",
                exif.date_taken.isoformat(sep=" ") if exif.date_taken else "",
            ]
        ).strip()

        if not self._f.include_full_metadata:
            return core

        cached = getattr(exif, "full_metadata_search_text", None)
        if cached is None:
            try:
                tags = get_all_exif_tags(exif.file_path)
            except Exception:
                tags = []
            cached = "\n".join(f"{k}: {v}" for k, v in tags)
            try:
                setattr(exif, "full_metadata_search_text", cached)
            except Exception:
                pass

        return (core + "\n" + (cached or "")).strip()

    def _match_query(self, exif: ExifData) -> bool:
        q = (self._f.query or "").strip()
        if not q:
            return True

        latlon = _try_parse_latlon(q)
        if latlon is not None:
            lat, lon = latlon
            eps = 1e-6
            if lat is not None and lon is None:
                for val in (exif.latitude, exif.longitude):
                    if val is not None and abs(val - lat) <= eps:
                        return True
                return False
            if lat is not None and lon is not None:
                if exif.latitude is None or exif.longitude is None:
                    return False
                return abs(exif.latitude - lat) <= eps and abs(exif.longitude - lon) <= eps

        text = self._build_row_search_text(exif)
        if self._f.partial_match:
            return q.casefold() in text.casefold()

        q_tokens = _tokenize(q)
        if not q_tokens:
            return True
        row_tokens = _tokenize(text)
        return q_tokens.issubset(row_tokens)

    def _match_filters(self, exif: ExifData) -> bool:
        # File type
        if self._f.file_type == "Images":
            if exif.is_video:
                return False
        elif self._f.file_type == "Videos":
            if not exif.is_video:
                return False

        # Extension
        if self._f.extensions:
            if exif.extension not in self._f.extensions:
                return False

        # GPS
        if self._f.gps == "Has GPS" and not exif.has_gps():
            return False
        if self._f.gps == "Missing GPS" and exif.has_gps():
            return False

        # Serial presence
        sn = (exif.serial_number or "").strip()
        if self._f.serial_presence == "Present" and not sn:
            return False
        if self._f.serial_presence == "Missing" and sn:
            return False

        # Date range
        if self._f.date_from or self._f.date_to:
            dt = exif.date_taken
            if dt is None:
                return False
            if self._f.date_from and dt < self._f.date_from:
                return False
            if self._f.date_to and dt > self._f.date_to:
                return False

        # Make/model/software multiselect (OR within field)
        if self._f.makes:
            if (exif.make or "").strip() not in self._f.makes:
                return False
        if self._f.models:
            if (exif.model or "").strip() not in self._f.models:
                return False
        if self._f.softwares:
            if (exif.software or "").strip() not in self._f.softwares:
                return False

        return True

    def filterAcceptsRow(self, source_row: int, source_parent: QModelIndex) -> bool:
        exif = self._source_row(source_row)
        if exif is None:
            return True
        if not self._match_filters(exif):
            return False
        return self._match_query(exif)

