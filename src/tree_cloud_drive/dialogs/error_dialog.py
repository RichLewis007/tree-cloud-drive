"""Error dialog with detailed stack trace display.

This module provides a user-friendly error dialog that:
- Displays full exception details and stack trace
- Provides copy-to-clipboard functionality for easy error reporting
- Uses a scrollable text area for long stack traces

The dialog is typically shown by the global exception hook when
uncaught exceptions occur, but can also be used programmatically.
"""
# Author: Rich Lewis - GitHub: @RichLewis007

from __future__ import annotations

import traceback

from PySide6.QtGui import QFont, QKeySequence, QTextCursor
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

from ..core.ui_loader import load_ui


class ErrorDialog(QDialog):
    """Dialog showing error details with copy-to-clipboard functionality."""

    def __init__(
        self,
        exc_type: type[BaseException],
        exc: BaseException,
        tb,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Unhandled Exception")
        self.setMinimumSize(700, 500)

        # Load UI from .ui file
        self._ui = load_ui("error_dialog.ui", self)
        main_layout = QVBoxLayout(self)
        main_layout.addWidget(self._ui)

        # Find widgets from UI file
        message_label = self._ui.findChild(QLabel, "messageLabel")
        text_edit = self._ui.findChild(QTextEdit, "errorDetailsTextEdit")
        button_box = self._ui.findChild(QDialogButtonBox, "buttonBox")

        if message_label is None or text_edit is None or button_box is None:
            raise RuntimeError("Required widgets not found in error_dialog.ui")

        # Message label
        message = (
            "An unexpected error occurred.\n\n"
            "Error details are shown below. Click 'Copy to Clipboard' to copy them."
        )
        message_label.setText(message)

        # Error details text area
        details = "".join(traceback.format_exception(exc_type, exc, tb))
        text_edit.setPlainText(details)
        # Font is already set in .ui file, but ensure it's correct
        font = QFont("Courier")
        text_edit.setFont(font)
        text_edit.moveCursor(QTextCursor.MoveOperation.End)

        # Buttons
        copy_button = QPushButton("Copy to Clipboard")
        copy_button.setShortcut(QKeySequence.StandardKey.Copy)

        def copy_details() -> None:
            from PySide6.QtWidgets import QApplication

            clipboard = QApplication.clipboard()
            text = f"Error Details:\n\n{details}"
            clipboard.setText(text)
            copy_button.setText("Copied!")
            copy_button.setEnabled(False)

        copy_button.clicked.connect(copy_details)
        button_box.addButton(copy_button, QDialogButtonBox.ButtonRole.ActionRole)
        button_box.accepted.connect(self.accept)
