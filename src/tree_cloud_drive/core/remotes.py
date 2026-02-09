"""Persist and retrieve rclone remotes cache."""
# Author: Rich Lewis - GitHub: @RichLewis007

from __future__ import annotations

import sqlite3
from pathlib import Path

from PySide6.QtCore import QStandardPaths


class RemoteStore:
    """SQLite-backed cache of rclone remotes."""

    def __init__(self, db_path: Path | None = None) -> None:
        self.db_path = db_path or self._default_db_path()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _default_db_path(self) -> Path:
        base = Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation))
        return base / "remotes.db"

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS remotes (
                    name TEXT PRIMARY KEY,
                    last_seen TEXT NOT NULL
                )
                """
            )

    def list(self) -> list[str]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT name FROM remotes ORDER BY name COLLATE NOCASE"
            ).fetchall()
        return [row[0] for row in rows]

    def replace(self, remotes: list[str]) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM remotes")
            conn.executemany(
                "INSERT INTO remotes(name, last_seen) VALUES(?, datetime('now'))",
                [(name,) for name in remotes],
            )
