"""Command palette dialog with searchable commands and keyboard shortcuts.

This module provides a command palette interface that allows users to:
- Search through available commands
- See command descriptions and keyboard shortcuts
- Execute commands via keyboard or mouse
- Navigate using arrow keys and Enter
"""
# Author: Rich Lewis - GitHub: @RichLewis007

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from PySide6.QtCore import QModelIndex, QSortFilterProxyModel, QStringListModel, Qt, Signal
from PySide6.QtWidgets import (
    QDialog,
    QLabel,
    QLineEdit,
    QListView,
    QVBoxLayout,
    QWidget,
)

from ..core.ui_loader import load_ui


@dataclass
class Command:
    """Represents a command in the command palette."""

    name: str
    description: str
    shortcut: str = ""
    action: Callable[[], None] | None = None


class CommandPalette(QDialog):
    """Command palette dialog with searchable commands and keyboard shortcuts."""

    command_selected = Signal(Command)

    def __init__(self, commands: list[Command], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Command Palette")
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Popup)
        self.setModal(True)

        self.commands = commands
        self.selected_command: Command | None = None

        # Load UI from .ui file
        self._ui = load_ui("command_palette.ui", self)
        main_layout = QVBoxLayout(self)
        main_layout.addWidget(self._ui)

        # Find widgets from UI file
        search_input = self._ui.findChild(QLineEdit, "searchInput")
        command_list = self._ui.findChild(QListView, "commandList")
        hint_label = self._ui.findChild(QLabel, "hintLabel")

        if search_input is None or command_list is None or hint_label is None:
            raise RuntimeError("Required widgets not found in command_palette.ui")

        self.search_input = search_input
        self.command_list = command_list
        self.hint_label = hint_label

        # Connect signals
        self.search_input.textChanged.connect(self._filter_commands)
        self.search_input.returnPressed.connect(self._select_first)
        self.command_list.doubleClicked.connect(lambda idx: self._on_item_double_clicked(idx))
        self.command_list.activated.connect(lambda idx: self._on_item_activated(idx))

        # Setup model and proxy
        self.model = QStringListModel(self)
        self.proxy_model = QSortFilterProxyModel(self)
        self.proxy_model.setSourceModel(self.model)
        self.proxy_model.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.command_list.setModel(self.proxy_model)

        # Populate commands
        self._update_command_list()

        # Set focus to search input
        self.search_input.setFocus()

    def _update_command_list(self) -> None:
        """Update the command list display."""
        display_texts = []
        for cmd in self.commands:
            display = f"{cmd.name} ({cmd.shortcut})" if cmd.shortcut else cmd.name
            if cmd.description:
                display += f" — {cmd.description}"
            display_texts.append(display)

        self.model.setStringList(display_texts)

    def _filter_commands(self, text: str) -> None:
        """Filter commands based on search text."""
        self.proxy_model.setFilterFixedString(text)
        if self.command_list.model().rowCount() > 0:
            self.command_list.setCurrentIndex(self.command_list.model().index(0, 0))

    def _select_first(self) -> None:
        """Select and execute the first filtered command."""
        if self.command_list.model().rowCount() > 0:
            index = self.command_list.currentIndex()
            if index.isValid():
                source_index = self.proxy_model.mapToSource(index)
                if 0 <= source_index.row() < len(self.commands):
                    cmd = self.commands[source_index.row()]
                    self.selected_command = cmd
                    self.accept()

    def _on_item_double_clicked(self, index: QModelIndex) -> None:
        """Handle double-click on command list item."""
        if index.isValid():
            source_index = self.proxy_model.mapToSource(index)
            if 0 <= source_index.row() < len(self.commands):
                cmd = self.commands[source_index.row()]
                self.selected_command = cmd
                self.accept()

    def _on_item_activated(self, index: QModelIndex) -> None:
        """Handle activation (Enter key) on command list item."""
        if index.isValid():
            source_index = self.proxy_model.mapToSource(index)
            if 0 <= source_index.row() < len(self.commands):
                cmd = self.commands[source_index.row()]
                self.selected_command = cmd
                self.accept()

    def keyPressEvent(self, event) -> None:  # type: ignore[override]
        """Handle keyboard input for command palette navigation."""
        if event.key() == Qt.Key.Key_Escape:
            self.reject()
            return
        if event.key() == Qt.Key.Key_Down:
            # Move selection down
            current = self.command_list.currentIndex()
            if current.isValid():
                below = current.sibling(current.row() + 1, current.column())
                if below.isValid():
                    self.command_list.setCurrentIndex(below)
            else:
                # Select first item if nothing selected
                if self.command_list.model().rowCount() > 0:
                    self.command_list.setCurrentIndex(self.command_list.model().index(0, 0))
            return
        if event.key() == Qt.Key.Key_Up:
            # Move selection up
            current = self.command_list.currentIndex()
            if current.isValid():
                above = current.sibling(current.row() - 1, current.column())
                if above.isValid():
                    self.command_list.setCurrentIndex(above)
            return
        # Let parent handle other keys (including text input)
        super().keyPressEvent(event)
