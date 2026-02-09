"""Main application window implementation.

This module provides the main window class that implements:
- Background worker execution with progress tracking
- Command palette integration
- Window state persistence (geometry and toolbar positions)
- Theme-aware UI

The UI layout is loaded from a Qt Designer .ui file, and widgets are
accessed programmatically for signal/slot connections.
"""
# Author: Rich Lewis - GitHub: @RichLewis007

from __future__ import annotations

import subprocess
from pathlib import Path

from PySide6.QtCore import QPoint, QSize, Qt, Slot, QStandardPaths
from PySide6.QtGui import (
    QAction,
    QBrush,
    QColor,
    QIcon,
    QKeySequence,
    QPainter,
    QPixmap,
    QPolygon,
    QShortcut,
    QTextCursor,
)
from PySide6.QtWidgets import (
    QComboBox,
    QDockWidget,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QTextEdit,
    QToolBar,
    QTreeWidget,
    QTreeWidgetItem,
    QWidget,
)

from .core.history import HistoryStore
from .core.paths import APP_NAME
from .core.settings import Settings
from .core.ui_loader import load_ui
from .core.window_state import WindowStateManager
from .core.workers import WorkContext, Worker, WorkerPool, WorkRequest
from .dialogs.command_palette import Command, CommandPalette
from .dialogs.download_dialog import DownloadDialog
from .dialogs.preferences import PreferencesDialog


class MainWindow(QMainWindow):
    """Main application window with comprehensive UI features and functionality."""

    def __init__(self, settings: Settings, instance_guard=None) -> None:
        super().__init__()
        self.settings = settings
        self.pool = WorkerPool()
        self.window_state = WindowStateManager(settings, self)
        self.action_prefs: QAction
        self.action_quit: QAction
        self.action_about: QAction
        self.label: QLabel
        self.remote_combo: QComboBox
        self.folder_combo: QComboBox
        self.folder_tree: QTreeWidget
        self.history_list: QListWidget
        self.clear_history_button: QPushButton
        self.debug_log_view: QTextEdit | None
        self.ui: QWidget
        self.tab_widget: QTabWidget
        self.view_menu: QMenu
        self.remote_worker: Worker[list[str]] | None
        self.folder_worker: Worker[list[str]] | None
        self.tree_worker: Worker[list[str]] | None
        self._tree_remote: str | None
        self._pending_history_folder: str | None
        self.history_store: HistoryStore

        self.setWindowTitle(APP_NAME)

        self.history_store = HistoryStore()
        self.debug_log_view = None

        self._build_actions()
        self._build_menus()  # Build menus before loading UI so dock widgets can add to View menu
        self._load_ui()
        self.remote_worker = None
        self.folder_worker = None
        self.tree_worker = None
        self._tree_remote = None
        self._pending_history_folder = None

        # Create horizontal toolbar with square icon buttons
        toolbar = self._create_toolbar()
        self.addToolBar(toolbar)

        self.remote_combo.currentIndexChanged.connect(self._on_remote_selected)
        self.folder_combo.currentIndexChanged.connect(self._on_folder_selected)
        self.folder_tree.itemExpanded.connect(self._on_tree_item_expanded)
        self.folder_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.folder_tree.customContextMenuRequested.connect(self._on_tree_context_menu)
        self.history_list.itemClicked.connect(self._on_history_item_clicked)

        # Restore window geometry and state
        self.window_state.restore_state()

        # Setup command palette
        self._setup_command_palette()

        # Load available remotes on startup
        self._load_remotes()

        # Debug log tab (optional)
        if self.settings.get_rclone_debug_enabled():
            self._ensure_debug_log_tab()

    def _build_actions(self) -> None:
        self.action_prefs = QAction("Preferences", self)
        self.action_prefs.triggered.connect(self.on_open_prefs)

        self.action_quit = QAction("Quit", self)
        self.action_quit.setShortcut(QKeySequence.StandardKey.Quit)
        self.action_quit.triggered.connect(self.on_quit)

        self.action_about = QAction("About", self)
        # Set role for macOS native menu integration
        # On macOS, this makes the action appear in the app menu
        # (e.g., "About tree-cloud-drive")
        self.action_about.setMenuRole(QAction.MenuRole.AboutRole)
        self.action_about.triggered.connect(self.on_about)

    def _create_toolbar(self) -> QToolBar:
        """Create a horizontal toolbar with square icon buttons."""
        toolbar = QToolBar("Main", self)
        toolbar.setObjectName("mainToolBar")  # Required for window state persistence

        # Set toolbar to use icon-only mode with square buttons
        toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)

        # Set icon size for square buttons (e.g., 32x32)
        icon_size = QSize(32, 32)
        toolbar.setIconSize(icon_size)

        # Create icons for actions
        self.action_prefs.setIcon(self._create_icon_for_action("preferences"))
        self.action_quit.setIcon(self._create_icon_for_action("quit"))

        # Add actions to toolbar
        toolbar.addAction(self.action_prefs)
        toolbar.addSeparator()  # Visual separator before quit button
        toolbar.addAction(self.action_quit)

        return toolbar

    def _create_icon_for_action(self, action_name: str) -> QIcon:
        """Create an icon for a toolbar action.

        Creates simple colored square icons with symbols.
        Can be extended to load from image files.
        """
        # Create a colored square pixmap for the icon
        size = 32
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)

        # Create painter to draw the icon
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Different colors for different actions
        colors = {
            "work": QColor(46, 204, 113),  # Green
            "preferences": QColor(155, 89, 182),  # Purple
            "quit": QColor(231, 76, 60),  # Red
        }
        color = colors.get(action_name, QColor(149, 165, 166))  # Gray default

        # Draw filled rounded rectangle
        margin = 2
        painter.fillRect(margin, margin, size - 2 * margin, size - 2 * margin, color)

        # Add a simple symbol based on action
        painter.setPen(QColor(255, 255, 255))  # White pen
        painter.setFont(painter.font())

        if action_name == "work":
            # Draw play icon (triangle)
            center = pixmap.rect().center()
            triangle = QPolygon(
                [
                    QPoint(center.x() - 6, center.y()),
                    QPoint(center.x() + 6, center.y() - 6),
                    QPoint(center.x() + 6, center.y() + 6),
                ]
            )
            painter.setBrush(QBrush(QColor(255, 255, 255)))
            painter.drawPolygon(triangle)
        elif action_name == "preferences":
            # Draw gear icon (simplified - circles)
            center = pixmap.rect().center()
            painter.drawEllipse(center, 6, 6)
            painter.drawEllipse(center, 10, 10)
        elif action_name == "quit":
            # Draw X icon (exit/close symbol)
            center = pixmap.rect().center()
            # Draw two diagonal lines forming an X
            margin = 8
            painter.drawLine(
                center.x() - margin, center.y() - margin, center.x() + margin, center.y() + margin
            )
            painter.drawLine(
                center.x() + margin, center.y() - margin, center.x() - margin, center.y() + margin
            )

        painter.end()

        return QIcon(pixmap)

    def _build_menus(self) -> None:
        file_menu = self.menuBar().addMenu("&File")
        file_menu.addAction(self.action_prefs)
        file_menu.addAction(self.action_quit)

        view_menu = self.menuBar().addMenu("&View")
        # Add toggle actions for dock widgets (will be populated after docks are created)
        self.view_menu = view_menu

        help_menu = self.menuBar().addMenu("&Help")
        help_menu.addAction(self.action_about)

    def _load_ui(self) -> None:
        # Create tab widget to organize different content areas
        self.tab_widget = QTabWidget(self)

        # Tab 1: Main UI
        self.ui = load_ui("main_window.ui", self)
        self.tab_widget.addTab(self.ui, "Main")

        # Set tab widget as central widget
        self.setCentralWidget(self.tab_widget)

        # Create dock widgets for additional content
        self._create_dock_widgets()

        label = self.ui.findChild(QLabel, "statusLabel")
        if label is None:
            raise RuntimeError("statusLabel not found in main_window.ui")
        self.label = label


        remote_combo = self.ui.findChild(QComboBox, "remoteCombo")
        if remote_combo is None:
            raise RuntimeError("remoteCombo not found in main_window.ui")
        self.remote_combo = remote_combo
        self.remote_combo.clear()
        self.remote_combo.addItem("Select a remote...")

        folder_combo = self.ui.findChild(QComboBox, "folderCombo")
        if folder_combo is None:
            raise RuntimeError("folderCombo not found in main_window.ui")
        self.folder_combo = folder_combo
        self.folder_combo.clear()
        self.folder_combo.addItem("Select a folder...")
        self.folder_combo.setEnabled(False)

        folder_tree = self.ui.findChild(QTreeWidget, "folderTree")
        if folder_tree is None:
            raise RuntimeError("folderTree not found in main_window.ui")
        self.folder_tree = folder_tree
        self.folder_tree.clear()
        self.folder_tree.setHeaderHidden(True)
        self._refresh_history_list()

    def _set_tree_placeholder(self, item: QTreeWidgetItem) -> None:
        placeholder = QTreeWidgetItem(["Loading..."])
        item.addChild(placeholder)

    def _clear_tree_placeholder(self, item: QTreeWidgetItem) -> None:
        for idx in range(item.childCount()):
            child = item.child(idx)
            if child and child.text(0) == "Loading...":
                item.removeChild(child)
                break

    def _set_item_loaded(self, item: QTreeWidgetItem, loaded: bool) -> None:
        item.setData(0, Qt.ItemDataRole.UserRole + 1, loaded)

    def _is_item_loaded(self, item: QTreeWidgetItem) -> bool:
        return bool(item.data(0, Qt.ItemDataRole.UserRole + 1))

    def _set_item_path(self, item: QTreeWidgetItem, path: str) -> None:
        item.setData(0, Qt.ItemDataRole.UserRole, path)

    def _get_item_path(self, item: QTreeWidgetItem) -> str:
        value = item.data(0, Qt.ItemDataRole.UserRole)
        return str(value) if value is not None else ""

    def _set_status(self, message: str, timeout_ms: int = 2000) -> None:
        self.label.setText(message)
        self.statusBar().showMessage(message, timeout_ms)

    def _run_rclone(self, args: list[str]) -> list[str]:
        result = subprocess.run(
            ["rclone", *args],
            check=False,
            capture_output=True,
            text=True,
        )
        if self.settings.get_rclone_debug_enabled():
            self._log_rclone_debug(args, result.stdout, result.stderr, result.returncode)
        if result.returncode != 0:
            msg = result.stderr.strip() or result.stdout.strip() or "Unknown rclone error"
            raise RuntimeError(msg)
        return [line.strip() for line in result.stdout.splitlines() if line.strip()]

    def _log_rclone_debug(
        self, args: list[str], stdout: str, stderr: str, returncode: int
    ) -> None:
        try:
            base = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)
            log_path = Path(base) / "rclone-debug.log"
            log_path.parent.mkdir(parents=True, exist_ok=True)
            with log_path.open("a", encoding="utf-8") as f:
                f.write("\n=== rclone run ===\n")
                f.write(f"Command: rclone {' '.join(args)}\n")
                f.write(f"Return code: {returncode}\n")
                if stdout:
                    f.write("STDOUT:\n")
                    f.write(stdout)
                    if not stdout.endswith("\n"):
                        f.write("\n")
                if stderr:
                    f.write("STDERR:\n")
                    f.write(stderr)
                    if not stderr.endswith("\n"):
                        f.write("\n")
            self._refresh_debug_log_view()
        except Exception:
            pass

    def _ensure_debug_log_tab(self) -> None:
        if self.debug_log_view is not None:
            return
        self.debug_log_view = QTextEdit(self)
        self.debug_log_view.setReadOnly(True)
        self.debug_log_view.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        self.tab_widget.addTab(self.debug_log_view, "Debug Log")
        self._refresh_debug_log_view()

    def _refresh_debug_log_view(self) -> None:
        if self.debug_log_view is None:
            return
        try:
            base = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)
            log_path = Path(base) / "rclone-debug.log"
            if not log_path.exists():
                self.debug_log_view.setPlainText("No debug log yet.")
                return
            self.debug_log_view.setPlainText(log_path.read_text(encoding="utf-8"))
            cursor = self.debug_log_view.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.End)
            self.debug_log_view.setTextCursor(cursor)
        except Exception:
            self.debug_log_view.setPlainText("Failed to load debug log.")

    def _load_remotes(self) -> None:
        if self.remote_worker is not None:
            self.remote_worker.cancel()
            self.remote_worker = None

        self.remote_combo.setEnabled(False)
        self.remote_combo.clear()
        self.remote_combo.addItem("Loading remotes...")
        self.folder_combo.setEnabled(False)
        self.folder_combo.clear()
        self.folder_combo.addItem("Select a folder...")
        self.folder_tree.clear()
        self._set_status("Loading cloud remotes...")

        def work(ctx: WorkContext) -> list[str]:
            ctx.check_cancelled()
            remotes = self._run_rclone(["listremotes"])
            return [remote.rstrip(":") for remote in remotes]

        def done(remotes: list[str]) -> None:
            self.remote_combo.clear()
            self.remote_combo.addItem("Select a remote...")
            if remotes:
                self.remote_combo.addItems(sorted(remotes))
            self.remote_combo.setEnabled(True)
            self._set_status("Select a cloud remote.")
            self.remote_worker = None

        def error(msg: str) -> None:
            self.remote_combo.clear()
            self.remote_combo.addItem("Select a remote...")
            self.remote_combo.setEnabled(True)
            self.remote_worker = None
            QMessageBox.critical(self, "Rclone error", msg)
            self._set_status("Failed to load remotes.")

        req = WorkRequest(fn=work, on_done=done, on_error=error)
        self.remote_worker = self.pool.submit(req)

    def _on_remote_selected(self) -> None:
        idx = self.remote_combo.currentIndex()
        if idx <= 0:
            self.folder_combo.setEnabled(False)
            self.folder_combo.clear()
            self.folder_combo.addItem("Select a folder...")
            self.folder_tree.clear()
            self._pending_history_folder = None
            return
        remote = self.remote_combo.currentText()
        self._load_top_level_dirs(remote)

    def _load_top_level_dirs(self, remote: str) -> None:
        if self.folder_worker is not None:
            self.folder_worker.cancel()
            self.folder_worker = None

        self.folder_combo.setEnabled(False)
        self.folder_combo.clear()
        self.folder_combo.addItem("Loading folders...")
        self.folder_tree.clear()
        self._set_status(f"Loading folders from {remote}...")

        def work(ctx: WorkContext) -> list[str]:
            ctx.check_cancelled()
            dirs = self._run_rclone(["lsf", "--dirs-only", "--max-depth", "1", f"{remote}:"])
            return [d.rstrip("/") for d in dirs]

        def done(dirs: list[str]) -> None:
            self.folder_combo.clear()
            self.folder_combo.addItem("Select a folder...")
            if dirs:
                self.folder_combo.addItems(sorted(dirs))
                self.folder_combo.setEnabled(True)
                self._set_status("Select a top-level folder.")
                if self._pending_history_folder and self._pending_history_folder in dirs:
                    idx = self.folder_combo.findText(self._pending_history_folder)
                    if idx >= 0:
                        self.folder_combo.setCurrentIndex(idx)
                self._pending_history_folder = None
            else:
                self.folder_combo.setEnabled(False)
                self._set_status("No folders found in remote.")
            self.folder_worker = None

        def error(msg: str) -> None:
            self.folder_combo.clear()
            self.folder_combo.addItem("Select a folder...")
            self.folder_combo.setEnabled(False)
            self.folder_worker = None
            QMessageBox.critical(self, "Rclone error", msg)
            self._set_status("Failed to load folders.")

        req = WorkRequest(fn=work, on_done=done, on_error=error)
        self.folder_worker = self.pool.submit(req)

    def _on_folder_selected(self) -> None:
        if self.remote_combo.currentIndex() <= 0:
            return
        idx = self.folder_combo.currentIndex()
        if idx <= 0:
            self.folder_tree.clear()
            return
        remote = self.remote_combo.currentText()
        folder = self.folder_combo.currentText()
        self.history_store.record(remote, folder)
        self._refresh_history_list()
        self._load_folder_tree(remote, folder)

    def _load_folder_tree(self, remote: str, folder: str) -> None:
        if self.tree_worker is not None:
            self.tree_worker.cancel()
            self.tree_worker = None

        self.folder_tree.clear()
        self._tree_remote = remote
        self._set_status(f"Loading {remote}:{folder}...")

        root_item = QTreeWidgetItem([folder])
        self._set_item_path(root_item, folder)
        self._set_item_loaded(root_item, False)
        self._set_tree_placeholder(root_item)
        self.folder_tree.addTopLevelItem(root_item)
        root_item.setExpanded(True)

        def work(ctx: WorkContext) -> list[str]:
            ctx.check_cancelled()
            dirs = self._run_rclone(
                ["lsf", "--dirs-only", "--max-depth", "1", f"{remote}:{folder}"]
            )
            return [d.rstrip("/") for d in dirs]

        def done(dirs: list[str]) -> None:
            self._clear_tree_placeholder(root_item)
            self._populate_children(root_item, dirs)
            self._set_item_loaded(root_item, True)
            self._set_status(f"Loaded {remote}:{folder}")
            self.tree_worker = None

        def error(msg: str) -> None:
            self.folder_tree.clear()
            self.tree_worker = None
            QMessageBox.critical(self, "Rclone error", msg)
            self._set_status("Failed to load folder tree.")

        req = WorkRequest(fn=work, on_done=done, on_error=error)
        self.tree_worker = self.pool.submit(req)

    def _populate_children(self, parent: QTreeWidgetItem, paths: list[str]) -> None:
        base_path = self._get_item_path(parent)
        seen: set[str] = set()
        for raw in sorted(paths):
            path = raw.strip().strip("/")
            if not path or path == ".":
                continue
            name = path.split("/")[-1]
            if name in seen:
                continue
            seen.add(name)
            item = QTreeWidgetItem([name])
            full_path = f"{base_path}/{path}" if base_path else path
            self._set_item_path(item, full_path)
            self._set_item_loaded(item, False)
            self._set_tree_placeholder(item)
            parent.addChild(item)

    def _on_tree_item_expanded(self, item: QTreeWidgetItem) -> None:
        if self._tree_remote is None:
            return
        if self._is_item_loaded(item):
            return
        path = self._get_item_path(item)
        if not path:
            return
        self._load_children_for_item(item, self._tree_remote, path)

    def _load_children_for_item(self, item: QTreeWidgetItem, remote: str, path: str) -> None:
        if self.tree_worker is not None:
            self.tree_worker.cancel()
            self.tree_worker = None

        self._set_status(f"Loading {remote}:{path}...")

        def work(ctx: WorkContext) -> list[str]:
            ctx.check_cancelled()
            dirs = self._run_rclone(["lsf", "--dirs-only", "--max-depth", "1", f"{remote}:{path}"])
            return [d.rstrip("/") for d in dirs]

        def done(dirs: list[str]) -> None:
            self._clear_tree_placeholder(item)
            self._populate_children(item, dirs)
            self._set_item_loaded(item, True)
            self._set_status(f"Loaded {remote}:{path}")
            self.tree_worker = None

        def error(msg: str) -> None:
            self._clear_tree_placeholder(item)
            self.tree_worker = None
            QMessageBox.critical(self, "Rclone error", msg)
            self._set_status("Failed to load folder.")

        req = WorkRequest(fn=work, on_done=done, on_error=error)
        self.tree_worker = self.pool.submit(req)

    def _refresh_history_list(self) -> None:
        self.history_list.clear()
        records = self.history_store.recent()
        if not records:
            item = QListWidgetItem("No history yet.")
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEnabled)
            self.history_list.addItem(item)
            return
        for rec in records:
            item = QListWidgetItem(f"{rec.remote}:{rec.folder}")
            font = item.font()
            font.setUnderline(True)
            item.setFont(font)
            item.setData(Qt.ItemDataRole.UserRole, (rec.remote, rec.folder))
            self.history_list.addItem(item)

    def _on_history_item_clicked(self, item: QListWidgetItem) -> None:
        data = item.data(Qt.ItemDataRole.UserRole)
        if not data:
            return
        remote, folder = data
        self._pending_history_folder = folder
        idx = self.remote_combo.findText(remote)
        if idx >= 0:
            self.remote_combo.setCurrentIndex(idx)

    def _on_clear_history(self) -> None:
        self.history_store.clear()
        self._refresh_history_list()

    def _on_tree_context_menu(self, pos) -> None:  # type: ignore[override]
        item = self.folder_tree.itemAt(pos)
        if item is None or self._tree_remote is None:
            return
        path = self._get_item_path(item)
        if not path:
            return
        menu = QMenu(self)
        download_action = menu.addAction("Download folder")
        selected = menu.exec(self.folder_tree.mapToGlobal(pos))
        if selected == download_action:
            remote_path = f"{self._tree_remote}:{path}"
            dlg = DownloadDialog(remote_path=remote_path, parent=self)
            dlg.exec()

    def _create_dock_widgets(self) -> None:
        """Create dock widgets for additional content areas."""
        # Info dock widget
        info_dock = QDockWidget("Information", self)
        info_dock.setObjectName("informationDock")  # Required for window state persistence

        # Load UI from .ui file
        info_widget = load_ui("information_dock.ui", self)
        history_list = info_widget.findChild(QListWidget, "historyList")
        if history_list is None:
            raise RuntimeError("historyList not found in information_dock.ui")
        self.history_list = history_list
        clear_btn = info_widget.findChild(QPushButton, "clearHistoryButton")
        if clear_btn is None:
            raise RuntimeError("clearHistoryButton not found in information_dock.ui")
        self.clear_history_button = clear_btn
        self.clear_history_button.clicked.connect(self._on_clear_history)
        info_dock.setWidget(info_widget)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, info_dock)
        # Add toggle action to View menu
        self.view_menu.addAction(info_dock.toggleViewAction())

        # Splitter demo dock (optional - can be shown via View menu)
        splitter_dock = QDockWidget("Splitter Demo", self)
        splitter_dock.setObjectName("splitterDemoDock")  # Required for window state persistence

        # Load UI from .ui file
        splitter_widget = load_ui("splitter_dock.ui", self)
        splitter_dock.setWidget(splitter_widget)
        # Start with info dock visible, splitter hidden
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, splitter_dock)
        splitter_dock.setVisible(False)
        # Add toggle action to View menu
        self.view_menu.addAction(splitter_dock.toggleViewAction())

    @Slot()
    def on_open_prefs(self) -> None:
        """Open the preferences dialog and handle theme changes."""
        dlg = PreferencesDialog(settings=self.settings, parent=self)
        dlg.theme_changed.connect(self._on_theme_changed)
        dlg.exec()
        if self.settings.get_rclone_debug_enabled():
            self._ensure_debug_log_tab()
        elif self.debug_log_view is not None:
            idx = self.tab_widget.indexOf(self.debug_log_view)
            if idx >= 0:
                self.tab_widget.removeTab(idx)
            self.debug_log_view = None

    def _on_theme_changed(self, theme: str) -> None:
        """Handle theme change from preferences dialog.

        Applies the new theme to both this window and the QApplication
        so dialogs inherit the theme.

        Args:
            theme: Theme name (e.g., "light" or "dark")
        """
        from .core.paths import qss_text

        try:
            qss = qss_text(theme)
            # Apply to this window
            self.setStyleSheet(qss)
            # Also update the QApplication so dialogs inherit the theme
            from PySide6.QtWidgets import QApplication

            app = QApplication.instance()
            if app and isinstance(app, QApplication):
                app.setStyleSheet(qss)
            self.statusBar().showMessage(f"Theme changed to {theme}", 2000)
        except FileNotFoundError:
            QMessageBox.warning(self, "Theme", f"Stylesheet not found for theme: {theme}")

    @Slot()
    def on_about(self) -> None:
        from .core.paths import app_version
        from .dialogs.about import AboutDialog

        dlg = AboutDialog(version=app_version(), release_notes_url="", parent=self)
        dlg.exec()

    @Slot()
    def on_quit(self) -> None:
        """Handle quit action with proper cleanup.

        Checks for running background workers and handles them appropriately.
        If a worker is running, asks the user if they want to cancel it and exit.
        """
        self.close()

    def _setup_command_palette(self) -> None:
        """Initialize command palette with commands and keyboard shortcut."""
        commands = [
            Command(
                name="Preferences",
                description="Open preferences dialog",
                shortcut="Ctrl+,",
                action=self.on_open_prefs,
            ),
            Command(
                name="About",
                description="Show about dialog",
                shortcut="",
                action=self.on_about,
            ),
            Command(
                name="Quit",
                description="Exit the application",
                shortcut="Ctrl+Q",
                action=lambda: [self.close(), None][1],  # type: ignore[return-value]
            ),
        ]

        # Create command palette shortcut (Ctrl+K or Ctrl+P)
        cmd_palette_shortcut = QShortcut(QKeySequence("Ctrl+K"), self)
        cmd_palette_shortcut.activated.connect(lambda: self._show_command_palette(commands))

        # Alternative shortcut (Ctrl+Shift+P like VS Code)
        cmd_palette_shortcut2 = QShortcut(QKeySequence("Ctrl+Shift+P"), self)
        cmd_palette_shortcut2.activated.connect(lambda: self._show_command_palette(commands))

    def _show_command_palette(self, commands: list[Command]) -> None:
        """Show the command palette dialog and execute selected command.

        Args:
            commands: List of Command objects to display in the palette
        """
        palette = CommandPalette(commands, self)
        # Position dialog centered horizontally near top of window
        palette.move(
            self.geometry().center().x() - palette.width() // 2,
            self.geometry().top() + 50,
        )
        # Execute command if one was selected
        if (
            palette.exec() == palette.DialogCode.Accepted
            and palette.selected_command
            and palette.selected_command.action
        ):
            palette.selected_command.action()

    def closeEvent(self, event) -> None:  # type: ignore[override]
        """Save window state before closing and cleanup resources."""
        # Save window state
        self.window_state.save_state()

        super().closeEvent(event)
