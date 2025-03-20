"""Qt Designer UI file loading.

This module provides utilities for loading Qt Designer .ui files at runtime
using QUiLoader. UI files are loaded from packaged assets, so they work
both from source and when installed from wheels.

The loader reads .ui files as bytes from the package and uses QUiLoader
to instantiate the widget hierarchy without requiring code generation.
"""
# Author: Rich Lewis - GitHub: @RichLewis007

from __future__ import annotations

from importlib.resources import files

from PySide6.QtCore import QBuffer, QIODevice
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import QWidget

_UI_DIR = "ui"  # Subdirectory within assets containing .ui files


def ui_bytes(filename: str) -> bytes:
    """Return raw bytes for a packaged Qt Designer .ui file."""
    return (files("tree_cloud_drive") / "assets" / _UI_DIR / filename).read_bytes()


def load_ui(filename: str, parent: QWidget | None = None) -> QWidget:
    """Load a Qt Designer .ui file into a QWidget using QUiLoader."""
    data = ui_bytes(filename)
    buffer = QBuffer()
    buffer.setData(data)
    buffer.open(QIODevice.OpenModeFlag.ReadOnly)
    try:
        loader = QUiLoader()
        widget = loader.load(buffer, parent)
    finally:
        buffer.close()
    if widget is None:
        raise RuntimeError(f"Failed to load UI file: {filename}")
    return widget
