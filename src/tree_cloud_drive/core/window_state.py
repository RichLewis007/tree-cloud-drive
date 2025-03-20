"""Window state persistence management.

This module provides functionality to save and restore window state:
- Window geometry (position, size)
- Window state (toolbars, dock widgets, etc.)

Separated from MainWindow to improve modularity and reusability.
"""
# Author: Rich Lewis - GitHub: @RichLewis007

from __future__ import annotations

from PySide6.QtWidgets import QMainWindow

from .settings import Settings


class WindowStateManager:
    """Manages window state persistence for QMainWindow."""

    def __init__(self, settings: Settings, window: QMainWindow) -> None:
        """Initialize window state manager.

        Args:
            settings: Settings instance for persisting window state
            window: The QMainWindow whose state will be managed
        """
        self.settings = settings
        self.window = window

    def restore_state(self) -> None:
        """Restore window geometry and state from settings.

        Called during window initialization to restore the previous session's
        window position, size, and toolbar/dock widget state. If no saved
        geometry exists (first run), the window is shown fullscreen by default.
        """
        geometry = self.settings.get_window_geometry()
        if geometry is not None:
            self.window.restoreGeometry(geometry)
        else:
            # No saved geometry - show fullscreen by default
            self.window.showMaximized()

        state = self.settings.get_window_state()
        if state is not None:
            self.window.restoreState(state)

    def save_state(self) -> None:
        """Save current window geometry and state to settings.

        Called when the window is closed (via closeEvent). Saves:
        - Window position and size
        - Window maximized/minimized state
        - Toolbar and dock widget positions
        - Any other widget states saved by Qt

        The saved state is restored on next application startup.
        """
        geometry = self.window.saveGeometry()
        state = self.window.saveState()
        # Convert QByteArray to bytes - QByteArray supports bytes() conversion in PySide6
        self.settings.set_window_geometry(bytes(geometry))  # type: ignore[arg-type]
        self.settings.set_window_state(bytes(state))  # type: ignore[arg-type]
