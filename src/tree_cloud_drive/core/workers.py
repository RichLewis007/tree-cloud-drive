"""Background worker system using QThreadPool and QRunnable.

This module provides a thread-safe system for executing background tasks
without blocking the main UI thread. Key features:
- Cooperative cancellation support
- Progress reporting via Qt signals
- Automatic callback handling on main thread
- Worker lifetime management to prevent crashes

Workers receive a WorkContext that provides:
- Cancellation checking via check_cancelled()
- Progress reporting via progress(percent, message)
"""
# Author: Rich Lewis - GitHub: @RichLewis007

from __future__ import annotations

import threading
from collections.abc import Callable
from dataclasses import dataclass
from typing import TypeVar, cast

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal, Slot

T = TypeVar("T")


class WorkerSignals[T](QObject):
    """Qt signals emitted by a background worker."""

    finished = Signal(object)  # result payload
    failed = Signal(str)  # error message
    cancelled = Signal()
    progress = Signal(int, str)  # percent, message


class WorkCancelled(Exception):
    """Raised by background work to indicate a cooperative cancellation."""


@dataclass(frozen=True)
class WorkContext:
    """Context passed to background tasks for progress and cancellation checks."""

    is_cancelled: Callable[[], bool]
    report_progress: Callable[[int, str], None]

    def check_cancelled(self) -> None:
        if self.is_cancelled():
            raise WorkCancelled()

    def progress(self, percent: int, message: str = "") -> None:
        self.report_progress(percent, message)


@dataclass
class WorkRequest[T]:
    """Bundle a callable (receives WorkContext) and optional callbacks."""

    fn: Callable[[WorkContext], T]
    on_done: Callable[[T], None] | None = None
    on_error: Callable[[str], None] | None = None
    on_cancel: Callable[[], None] | None = None
    on_progress: Callable[[int, str], None] | None = None


class Worker[T](QRunnable):
    """Execute a WorkRequest in a QThreadPool and signal completion."""

    def __init__(self, req: WorkRequest[T]) -> None:
        super().__init__()
        # Qt can auto-delete QRunnable objects, but in Python we manage lifetime
        # explicitly to avoid premature GC that can crash PySide/Shiboken.
        self.setAutoDelete(False)
        self.req = req
        self.signals: WorkerSignals[T] = WorkerSignals()
        self._cancelled = threading.Event()

        if self.req.on_done:
            self.signals.finished.connect(self._handle_done)
        if self.req.on_error:
            self.signals.failed.connect(self._handle_error)
        if self.req.on_cancel:
            self.signals.cancelled.connect(self._handle_cancel)
        if self.req.on_progress:
            self.signals.progress.connect(self._handle_progress)

    @Slot(object)
    def _handle_done(self, result: object) -> None:
        assert self.req.on_done is not None
        self.req.on_done(cast(T, result))

    @Slot(str)
    def _handle_error(self, msg: str) -> None:
        assert self.req.on_error is not None
        self.req.on_error(msg)

    @Slot()
    def _handle_cancel(self) -> None:
        assert self.req.on_cancel is not None
        self.req.on_cancel()

    @Slot(int, str)
    def _handle_progress(self, percent: int, message: str) -> None:
        assert self.req.on_progress is not None
        self.req.on_progress(percent, message)

    def cancel(self) -> None:
        self._cancelled.set()

    def _emit_progress(self, percent: int, message: str) -> None:
        bounded = max(0, min(100, int(percent)))
        self.signals.progress.emit(bounded, message)

    def run(self) -> None:
        ctx = WorkContext(self._cancelled.is_set, self._emit_progress)
        try:
            result = self.req.fn(ctx)
            if self._cancelled.is_set():
                self.signals.cancelled.emit()
                return
            self.signals.finished.emit(result)
        except WorkCancelled:
            self.signals.cancelled.emit()
        except Exception as e:
            self.signals.failed.emit(str(e))


class WorkerPool:
    """Small wrapper around QThreadPool for submission convenience."""

    def __init__(self) -> None:
        self.pool = QThreadPool.globalInstance()
        self._workers: set[Worker[object]] = set()

    def submit[T](self, req: WorkRequest[T]) -> Worker[T]:
        worker = Worker(req=req)
        # Keep a strong reference to prevent the worker from being GC'd mid-run.
        self._workers.add(cast(Worker[object], worker))

        def _cleanup(*_: object) -> None:
            self._workers.discard(cast(Worker[object], worker))

        worker.signals.finished.connect(_cleanup)
        worker.signals.failed.connect(_cleanup)
        worker.signals.cancelled.connect(_cleanup)
        self.pool.start(worker)
        return worker
