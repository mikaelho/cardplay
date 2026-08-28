#!/usr/bin/env bash
# Export game notes (keeper notes, hex maps, characters & cards, situations)
# to a Markdown tree under notes/. Re-runnable; rebuilds the tree each time.
set -euo pipefail
cd "$(dirname "$0")"
PYTHONPATH=. DJANGO_SETTINGS_MODULE=settings uv run django-admin export_notes "$@"
