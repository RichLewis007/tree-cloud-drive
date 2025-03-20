"""Settings management using QSettings.

This module provides a typed wrapper around Qt's QSettings for persistent
application settings. It centralizes setting keys and provides convenience
methods for common data types (strings, window state, etc.).

Settings are automatically persisted to platform-appropriate locations:
- macOS: ~/Library/Preferences/
- Windows: Registry
- Linux: ~/.config/
"""
# Author: Rich Lewis - GitHub: @RichLewis007

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QSettings


@dataclass(frozen=True)
class SettingsKeys:
    """Centralize QSettings keys used by the application."""

    theme: str = "ui/theme"
    window_geometry: str = "window/geometry"
    window_state: str = "window/state"
    splash_screen_seconds: str = "ui/splash_screen_seconds"


class Settings:
    """Wrapper around QSettings with convenience getters/setters."""

    def __init__(self) -> None:
        self._qs = QSettings()
        self.keys = SettingsKeys()

    def get_str(self, key: str, default: str = "") -> str:
        value = self._qs.value(key, defaultValue=default)
        return str(value) if value is not None else default

    def set_str(self, key: str, value: str) -> None:
        self._qs.setValue(key, value)

    def get_theme(self) -> str:
        return self.get_str(self.keys.theme, "light")

    def set_theme(self, theme: str) -> None:
        self.set_str(self.keys.theme, theme)

    def get_window_geometry(self) -> bytes | None:
        """Get saved window geometry as bytes, or None if not set."""
        value = self._qs.value(self.keys.window_geometry)
        if value is None:
            return None
        if isinstance(value, bytes):
            return value
        if isinstance(value, str):
            try:
                return value.encode("latin1")
            except UnicodeEncodeError:
                return None
        return None

    def set_window_geometry(self, geometry: bytes) -> None:
        """Save window geometry as bytes."""
        self._qs.setValue(self.keys.window_geometry, geometry)

    def get_window_state(self) -> bytes | None:
        """Get saved window state as bytes, or None if not set."""
        value = self._qs.value(self.keys.window_state)
        if value is None:
            return None
        if isinstance(value, bytes):
            return value
        if isinstance(value, str):
            try:
                return value.encode("latin1")
            except UnicodeEncodeError:
                return None
        return None

    def set_window_state(self, state: bytes) -> None:
        """Save window state (toolbars, docks, etc.) as bytes."""
        self._qs.setValue(self.keys.window_state, state)

    def reset_to_defaults(self) -> None:
        """Reset all settings to their default values."""
        self._qs.clear()

    def validate_theme(self, theme: str) -> bool:
        """Validate that theme is one of the supported themes."""
        return theme in ("light", "dark")

    def get_splash_screen_seconds(self) -> int | None:
        """Get splash screen display duration in seconds.

        Returns:
            Number of seconds to show splash screen (0 = show until user clicks OK),
            or None to not show it (default).
        """
        value = self._qs.value(self.keys.splash_screen_seconds)
        if value is None:
            return None
        try:
            return int(str(value))
        except (ValueError, TypeError):
            return None

    def set_splash_screen_seconds(self, seconds: int | None) -> None:
        """Set splash screen display duration in seconds.

        Args:
            seconds: Number of seconds to show splash screen (0 = show until user clicks OK),
                    or None to not show it (removes the setting).
        """
        if seconds is None:
            self._qs.remove(self.keys.splash_screen_seconds)
        else:
            self._qs.setValue(self.keys.splash_screen_seconds, seconds)
