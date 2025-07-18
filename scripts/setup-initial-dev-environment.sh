#!/usr/bin/env bash
# Author: Rich Lewis - GitHub: @RichLewis007
# Setup script for development environment
# Installs dependencies and the package in editable mode

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

echo "🔧 Setting up development environment..."
echo ""

# Sync dependencies
echo "📦 Syncing dependencies..."
uv sync --dev

# Install package in editable mode
echo "📦 Installing package in editable mode..."
uv pip install -e .

echo ""
echo "✅ Setup complete!"
echo ""
echo "You can now run:"
echo "  - uv run pytest          # Run tests"
echo "  - uv run tree-cloud-drive  # Run the app"
echo "  - ./menu.sh               # Open development menu"
