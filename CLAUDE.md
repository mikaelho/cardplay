# Cardplay

## Architecture

- Starlette app with **PyView** (LiveView-style) frontend, **Django ORM** for data.
- Templates use **ibis** (not Jinja2, not Django templates).
- `phx-submit` sends values as **lists**.
- All ORM calls from async PyView code require `sync_to_async`.
- **alive** is a generic sibling package (`../alive`) providing CRUD UI, `AliveMixin`/`AliveConf`, visibility, drag-drop, JS hooks. All cardplay-specific behavior is in this repo via hooks.
- `cards/alive_hooks.py`: all cardplay-specific LiveView event handlers, mount/refresh/params hooks, data loading.
- Frontend: Tailwind CSS v4 (browser build) + DaisyUI 5 (CDN). Tailwind v4 browser build cannot generate responsive variants of DaisyUI component classes — use manual CSS media queries.

## Django management commands

```bash
PYTHONPATH=. DJANGO_SETTINGS_MODULE=settings uv run django-admin <command>
```

Examples:
```bash
# Run migrations
PYTHONPATH=. DJANGO_SETTINGS_MODULE=settings uv run django-admin migrate

# Create migrations
PYTHONPATH=. DJANGO_SETTINGS_MODULE=settings uv run django-admin makemigrations cards --name <name>
```

## Running the app

```bash
uv run python app.py
```
