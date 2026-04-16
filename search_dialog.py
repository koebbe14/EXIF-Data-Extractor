from __future__ import annotations

from dataclasses import dataclass

from PyQt5.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)


@dataclass
class SearchSettings:
    query: str
    partial_match: bool
    include_full_metadata: bool


class SearchDialog(QDialog):
    def __init__(self, parent, initial: SearchSettings):
        super().__init__(parent)
        self.setWindowTitle("Search")

        self._initial = initial
        self._result: SearchSettings | None = None
        self._cleared = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        title = QLabel("Search")
        title.setStyleSheet("font-size: 14pt; font-weight: 600;")
        layout.addWidget(title)

        subtitle = QLabel(
            "Search filenames and extracted metadata. GPS formats like `34.0522` or `34.0522,-118.2437` are supported."
        )
        subtitle.setStyleSheet("color: #888;")
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)

        query_group = QGroupBox("Query")
        ql = QVBoxLayout(query_group)
        ql.setContentsMargins(12, 10, 12, 12)
        ql.setSpacing(8)

        self.query_edit = QLineEdit()
        self.query_edit.setPlaceholderText("Type to search…")
        self.query_edit.setClearButtonEnabled(True)
        self.query_edit.setText(initial.query or "")
        self.query_edit.setMinimumWidth(640)
        ql.addWidget(self.query_edit)
        layout.addWidget(query_group)

        options_group = QGroupBox("Options")
        ol = QVBoxLayout(options_group)
        ol.setContentsMargins(12, 10, 12, 12)
        ol.setSpacing(6)

        self.partial_cb = QCheckBox("Partial match (substring)")
        self.partial_cb.setChecked(bool(initial.partial_match))
        ol.addWidget(self.partial_cb)

        self.full_meta_cb = QCheckBox("Include full metadata (slower)")
        self.full_meta_cb.setChecked(bool(initial.include_full_metadata))
        ol.addWidget(self.full_meta_cb)

        layout.addWidget(options_group)

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

        self.setMinimumWidth(720)

    def _on_apply(self):
        self._result = SearchSettings(
            query=self.query_edit.text(),
            partial_match=self.partial_cb.isChecked(),
            include_full_metadata=self.full_meta_cb.isChecked(),
        )
        self.accept()

    def _on_clear(self):
        self.query_edit.setText("")
        self.partial_cb.setChecked(True)
        self.full_meta_cb.setChecked(False)
        self._cleared = True
        self._on_apply()

    def result(self) -> SearchSettings | None:
        return self._result

