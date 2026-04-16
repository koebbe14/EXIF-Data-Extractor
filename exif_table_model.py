from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, List, Optional

from PyQt5.QtCore import QAbstractTableModel, QModelIndex, Qt

from data_model import ExifData


@dataclass(frozen=True)
class ExifColumn:
    header: str
    key: str


_COLUMNS: List[ExifColumn] = [
    ExifColumn("Thumbnail", "thumbnail"),
    ExifColumn("File Name", "file_name"),
    ExifColumn("Timestamp", "date_taken"),
    ExifColumn("Latitude", "latitude"),
    ExifColumn("Longitude", "longitude"),
    ExifColumn("Altitude", "altitude"),
    ExifColumn("Make", "make"),
    ExifColumn("Model", "model"),
    ExifColumn("Serial Number", "serial_number"),
    ExifColumn("Software", "software"),
]


class ExifTableModel(QAbstractTableModel):
    def __init__(self, exif_data: Optional[List[ExifData]] = None, parent=None):
        super().__init__(parent)
        self._rows: List[ExifData] = list(exif_data or [])

    def set_rows(self, rows: List[ExifData]) -> None:
        self.beginResetModel()
        self._rows = list(rows)
        self.endResetModel()

    def append_rows(self, rows: List[ExifData]) -> None:
        if not rows:
            return
        start = len(self._rows)
        end = start + len(rows) - 1
        self.beginInsertRows(QModelIndex(), start, end)
        self._rows.extend(rows)
        self.endInsertRows()

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        if parent.isValid():
            return 0
        return len(self._rows)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        if parent.isValid():
            return 0
        return len(_COLUMNS)

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.DisplayRole):
        if role != Qt.DisplayRole:
            return None
        if orientation == Qt.Horizontal:
            if 0 <= section < len(_COLUMNS):
                return _COLUMNS[section].header
        return None

    def flags(self, index: QModelIndex):
        if not index.isValid():
            return Qt.NoItemFlags
        return Qt.ItemIsEnabled | Qt.ItemIsSelectable

    def get_row(self, row: int) -> Optional[ExifData]:
        if 0 <= row < len(self._rows):
            return self._rows[row]
        return None

    def rows(self) -> List[ExifData]:
        return list(self._rows)

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole):
        if not index.isValid():
            return None

        row = index.row()
        col = index.column()
        if not (0 <= row < len(self._rows)) or not (0 <= col < len(_COLUMNS)):
            return None

        exif = self._rows[row]
        key = _COLUMNS[col].key

        if role == Qt.DisplayRole:
            if key == "thumbnail":
                return ""
            if key == "file_name":
                return exif.file_name or ""
            if key == "date_taken":
                return exif.date_taken.strftime("%Y-%m-%d %H:%M:%S") if exif.date_taken else ""
            if key == "latitude":
                return f"{exif.latitude:.6f}" if exif.latitude is not None else ""
            if key == "longitude":
                return f"{exif.longitude:.6f}" if exif.longitude is not None else ""
            if key == "altitude":
                return f"{exif.altitude:.2f}" if exif.altitude is not None else ""
            if key == "make":
                return exif.make or ""
            if key == "model":
                return exif.model or ""
            if key == "serial_number":
                return exif.serial_number or ""
            if key == "software":
                return exif.software or ""
            return ""

        if role == Qt.ToolTipRole and key == "date_taken":
            return "EXIF encoded date: DateTimeOriginal, DateTimeDigitized, or DateTime"

        if role == Qt.DecorationRole and key == "thumbnail":
            pixmap = getattr(exif, "thumbnail_qpixmap", None)
            if pixmap is not None:
                return pixmap
            return None

        if role == Qt.TextAlignmentRole:
            if key == "thumbnail":
                return int(Qt.AlignCenter)
            return int(Qt.AlignVCenter | Qt.AlignLeft)

        if role == Qt.UserRole:
            if key == "file_name":
                return exif.file_name or ""
            if key == "date_taken":
                return exif.date_taken or datetime.min
            if key == "latitude":
                return exif.latitude
            if key == "longitude":
                return exif.longitude
            if key == "altitude":
                return exif.altitude
            if key == "make":
                return (exif.make or "").casefold()
            if key == "model":
                return (exif.model or "").casefold()
            if key == "serial_number":
                return (exif.serial_number or "").casefold()
            if key == "software":
                return (exif.software or "").casefold()
            if key == "thumbnail":
                return 0
            return None

        return None

