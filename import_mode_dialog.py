from __future__ import annotations

from dataclasses import dataclass

from PyQt5.QtWidgets import (
    QButtonGroup,
    QDialog,
    QDialogButtonBox,
    QLabel,
    QRadioButton,
    QVBoxLayout,
)


@dataclass(frozen=True)
class ImportChoice:
    mode: str  # "replace" | "append" | "cancel"


def choose_import_mode(parent, default_mode: str = "replace") -> ImportChoice:
    dlg = QDialog(parent)
    dlg.setWindowTitle("Import Options")

    layout = QVBoxLayout(dlg)
    layout.addWidget(
        QLabel(
            "You already have results loaded.\n\n"
            "Do you want to replace the existing results, or append the new files to them?"
        )
    )

    rb_replace = QRadioButton("Replace (clear existing results)")
    rb_append = QRadioButton("Append (add to existing results)")

    group = QButtonGroup(dlg)
    group.addButton(rb_replace)
    group.addButton(rb_append)

    if default_mode == "append":
        rb_append.setChecked(True)
    else:
        rb_replace.setChecked(True)

    layout.addWidget(rb_replace)
    layout.addWidget(rb_append)

    buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
    layout.addWidget(buttons)

    buttons.accepted.connect(dlg.accept)
    buttons.rejected.connect(dlg.reject)

    if dlg.exec_() != QDialog.Accepted:
        return ImportChoice(mode="cancel")

    mode = "append" if rb_append.isChecked() else "replace"
    return ImportChoice(mode=mode)
