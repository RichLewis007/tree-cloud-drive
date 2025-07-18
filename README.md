# tree-cloud-drive

A small, clean PySide6 starter project focused on clarity, separation of concerns, and
practical best practices. It keeps the UI simple while demonstrating how to structure
an application so it is easy to grow.

## What this includes

- **Main window + dock widgets** built from Qt Designer `.ui` files
- **Background work demo** with progress reporting and cancellation
- **Preferences dialog** (theme + splash screen settings)
- **Command palette** for quick actions (`Ctrl+K`, `Ctrl+Shift+P`)
- **Window state persistence** (geometry + dock/toolbar state)
- **Single-instance guard** (prevents multiple running instances)
- **Error dialog** for uncaught exceptions
- **Theming via QSS** (light/dark)

## Project layout

```
src/tree_cloud_drive/
  app.py              # App startup, exception hook, theme, icon
  main_window.py      # Main window UI + interactions
  core/
    exceptions.py     # Global exception hook
    paths.py          # Version + packaged asset helpers
    settings.py       # QSettings wrapper
    ui_loader.py      # Qt Designer .ui loader
    window_state.py   # Save/restore window state
    workers.py        # Background worker framework
  dialogs/
    about.py
    command_palette.py
    error_dialog.py
    preferences.py
  assets/
    ui/               # Qt Designer .ui files
    styles.qss
    styles_dark.qss
    app_icon.png
```

## Setup

```bash
./scripts/setup.sh
```

Or manually:

```bash
uv sync --dev
uv pip install -e .
```

## Run

```bash
uv run tree-cloud-drive
```

## Dev checks

```bash
uv run pytest
uv run ruff check .
uv run ruff format .
uv run pyright
```

## Where to start

- `src/tree_cloud_drive/app.py` – startup + theme/icon wiring
- `src/tree_cloud_drive/main_window.py` – UI wiring + background work demo
- `src/tree_cloud_drive/core/ui_loader.py` – .ui loader
- `src/tree_cloud_drive/core/workers.py` – worker framework
- `src/tree_cloud_drive/dialogs/preferences.py` – preferences dialog
