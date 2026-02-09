"""Persist and retrieve remote/folder selection history."""
# Author: Rich Lewis - GitHub: @RichLewis007

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QStandardPaths


@dataclass(frozen=True)
class SelectionRecord:
    remote: str
    folder: str
    last_used: str


class HistoryStore:
    """SQLite-backed history of remote/folder selections."""

    def __init__(self, db_path: Path | None = None) -> None:
        self.db_path = db_path or self._default_db_path()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _default_db_path(self) -> Path:
        base = Path(
            QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)
        )
        return base / "history.db"

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS selections (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    remote TEXT NOT NULL,
                    folder TEXT NOT NULL,
                    last_used TEXT NOT NULL,
                    UNIQUE(remote, folder)
                )
                """
            )

    def record(self, remote: str, folder: str) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO selections(remote, folder, last_used)
                VALUES(?, ?, datetime('now'))
                ON CONFLICT(remote, folder)
                DO UPDATE SET last_used = datetime('now')
                """,
                (remote, folder),
            )

    def recent(self, limit: int = 50) -> list[SelectionRecord]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT remote, folder, last_used
                FROM selections
                ORDER BY last_used DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [SelectionRecord(remote=r[0], folder=r[1], last_used=r[2]) for r in rows]

    def clear(self) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM selections")
