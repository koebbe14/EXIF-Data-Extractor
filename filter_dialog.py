from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, Optional, Set

from PyQt5.QtCore import QDate, Qt
from PyQt5.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
)


def _set_checked_items(list_widget: QListWidget, selected: Set[str]) -> None:
    selected = {s for s in selected if s}
    for i in range(list_widget.count()):
        it = list_widget.item(i)
        if it is None:
            continue
        it.setCheckState(Qt.Checked if it.text() in selected else Qt.Unchecked)


def _get_checked_items(list_widget: QListWidget) -> Set[str]:
    out: Set[str] = set()
    for i in range(list_widget.count()):
        it = list_widget.item(i)
        if it is None:
            continue
        if it.checkState() == Qt.Checked:
            out.add(it.text())
    return out


def _make_checklist(options: Iterable[str]) -> QListWidget:
    w = QListWidget()
    w.setMinimumHeight(120)
    for opt in options:
        it = QListWidgetItem(str(opt))
        it.setFlags(it.flags() | Qt.ItemIsUserCheckable)
        it.setCheckState(Qt.Unchecked)
        w.addItem(it)
    return w


@dataclass
class FilterSettings:
    file_type: str
    gps: str
    serial_presence: str
    date_from: Optional[datetime]
    date_to: Optional[datetime]
    extensions: Set[str]
    makes: Set[str]
    models: Set[str]
    softwares: Set[str]


class FilterDialog(QDialog):
    def __init__(self, parent, initial: FilterSettings, options: dict):
        super().__init__(parent)
        self.setWindowTitle("Filter")
        self._result: FilterSettings | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        title = QLabel("Filter")
        title.setStyleSheet("font-size: 14pt; font-weight: 600;")
        layout.addWidget(title)

        subtitle = QLabel("Narrow results by file type, GPS availability, date range, and device attributes.")
        subtitle.setStyleSheet("color: #888;")
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)

        # --- General filters ---
        general_group = QGroupBox("General")
        gl = QFormLayout(general_group)
        gl.setContentsMargins(12, 10, 12, 12)
        gl.setHorizontalSpacing(16)
        gl.setVerticalSpacing(8)

        self.file_type_combo = QComboBox()
        self.file_type_combo.addItems(["All", "Images", "Videos"])
        self.file_type_combo.setCurrentText(initial.file_type or "All")
        gl.addRow("File type:", self.file_type_combo)

        self.gps_combo = QComboBox()
        self.gps_combo.addItems(["Any", "Has GPS", "Missing GPS"])
        self.gps_combo.setCurrentText(initial.gps or "Any")
        gl.addRow("GPS:", self.gps_combo)

        self.serial_combo = QComboBox()
        self.serial_combo.addItems(["Any", "Present", "Missing"])
        self.serial_combo.setCurrentText(initial.serial_presence or "Any")
        gl.addRow("Serial number:", self.serial_combo)

        layout.addWidget(general_group)

        # --- Date range ---
        date_group = QGroupBox("Date range")
        dl = QGridLayout(date_group)
        dl.setContentsMargins(12, 10, 12, 12)
        dl.setHorizontalSpacing(12)
        dl.setVerticalSpacing(8)

        self.date_from_enabled = QCheckBox("From")
        self.date_from_enabled.setChecked(bool(initial.date_from))
        dl.addWidget(self.date_from_enabled, 0, 0)
        self.date_from = QDateEdit()
        self.date_from.setCalendarPopup(True)
        self.date_from.setEnabled(self.date_from_enabled.isChecked())
        self.date_from_enabled.toggled.connect(self.date_from.setEnabled)
        if initial.date_from:
            self.date_from.setDate(QDate(initial.date_from.year, initial.date_from.month, initial.date_from.day))
        else:
            self.date_from.setDate(QDate.currentDate().addYears(-1))
        dl.addWidget(self.date_from, 0, 1)

        self.date_to_enabled = QCheckBox("To")
        self.date_to_enabled.setChecked(bool(initial.date_to))
        dl.addWidget(self.date_to_enabled, 0, 2)
        self.date_to = QDateEdit()
        self.date_to.setCalendarPopup(True)
        self.date_to.setEnabled(self.date_to_enabled.isChecked())
        self.date_to_enabled.toggled.connect(self.date_to.setEnabled)
        if initial.date_to:
            self.date_to.setDate(QDate(initial.date_to.year, initial.date_to.month, initial.date_to.day))
        else:
            self.date_to.setDate(QDate.currentDate())
        dl.addWidget(self.date_to, 0, 3)

        dl.setColumnStretch(4, 1)
        layout.addWidget(date_group)

        # --- Category multi-select lists ---
        cat_group = QGroupBox("Categories (check items to include)")
        cl = QGridLayout(cat_group)
        cl.setContentsMargins(12, 10, 12, 12)
        cl.setHorizontalSpacing(12)
        cl.setVerticalSpacing(4)

        headers = ["Extensions", "Make", "Model", "Software"]
        self.ext_list = _make_checklist(options.get("extensions", []))
        self.make_list = _make_checklist(options.get("makes", []))
        self.model_list = _make_checklist(options.get("models", []))
        self.software_list = _make_checklist(options.get("softwares", []))

        _set_checked_items(self.ext_list, initial.extensions or set())
        _set_checked_items(self.make_list, initial.makes or set())
        _set_checked_items(self.model_list, initial.models or set())
        _set_checked_items(self.software_list, initial.softwares or set())

        lists = [self.ext_list, self.make_list, self.model_list, self.software_list]
        for col, (hdr, lw) in enumerate(zip(headers, lists)):
            lbl = QLabel(hdr)
            lbl.setStyleSheet("font-weight: 600;")
            cl.addWidget(lbl, 0, col)
            cl.addWidget(lw, 1, col)

        layout.addWidget(cat_group, 1)

        # --- Buttons ---
        buttons_row = QHBoxLayout()
        clear_btn = QPushButton("Clear")
        clear_btn.clicked.connect(self._on_clear)
        buttons_row.addWidget(clear_btn)
        buttons_row.addStretch()

        buttons = QDialogButtonBox(QDialogButtonBox.Apply | QDialogButtonBox.Close)
        buttons.button(QDialogButtonBox.Apply).clicked.connect(self._on_apply)
        buttons.rejected.connect(self.reject)
        buttons_row.addWidget(buttons)
        layout.addLayout(buttons_row)

        self.setMinimumWidth(860)
        self.resize(920, 580)

    def _on_apply(self):
        df = None
        dt = None
        if self.date_from_enabled.isChecked():
            qd = self.date_from.date()
            df = datetime(qd.year(), qd.month(), qd.day(), 0, 0, 0)
        if self.date_to_enabled.isChecked():
            qd = self.date_to.date()
            dt = datetime(qd.year(), qd.month(), qd.day(), 23, 59, 59)

        self._result = FilterSettings(
            file_type=self.file_type_combo.currentText(),
            gps=self.gps_combo.currentText(),
            serial_presence=self.serial_combo.currentText(),
            date_from=df,
            date_to=dt,
            extensions=_get_checked_items(self.ext_list),
            makes=_get_checked_items(self.make_list),
            models=_get_checked_items(self.model_list),
            softwares=_get_checked_items(self.software_list),
        )
        self.accept()

    def _on_clear(self):
        self.file_type_combo.setCurrentText("All")
        self.gps_combo.setCurrentText("Any")
        self.serial_combo.setCurrentText("Any")
        self.date_from_enabled.setChecked(False)
        self.date_to_enabled.setChecked(False)
        _set_checked_items(self.ext_list, set())
        _set_checked_items(self.make_list, set())
        _set_checked_items(self.model_list, set())
        _set_checked_items(self.software_list, set())
        self._on_apply()

    def result(self) -> FilterSettings | None:
        return self._result
