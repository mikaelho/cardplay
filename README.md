# Cardplay

A card-based roleplaying game management application.

## Architecture

Starlette app using **PyView** for the interactive frontend and **Django ORM** for data access. Django admin is served alongside via WSGIMiddleware.

### Key points

- **PyView + Starlette**: `app.py` creates the PyView app, mounts static files, and wires up middleware (session, player context).
    - PyView uses **ibis templates** — similar to but distinct from Jinja2/Django templates.
    - phx-submit sends values as **lists**.
- **Django ORM**: Models live in `cards/models/`. Since the app is async, all ORM calls from the Starlette/PyView layer require `sync_to_async` or equivalent.
- **Django Admin**: Mounted at `/admin/` via WSGIMiddleware. All models are registered in `cards/admin.py`.
- **alive package**: Installed as an editable sibling (`../alive`). Provides generic CRUD UI generation, `AliveMixin`/`AliveConf` for model configuration, visibility filtering, drag-drop support, and JS hooks. Modify alive when generic behavior needs to change; keep cardplay-specific logic in this repo.
- **cards app**: Contains all domain models and logic specific to playing card-based RPGs — games, players, characters, cards, hands, situations, hex maps, sheets/tags, and visibility rules (`cards/visibility.py`).
- **Frontend**: Tailwind CSS v4 (browser build) + DaisyUI 5 (CDN). Custom JS hooks in `staticfiles/alive/js/` for hex map interaction, drag-drop (Sortable.js), and keyboard shortcuts. Note: Tailwind v4 browser build cannot generate responsive variants of DaisyUI component classes (e.g. `lg:drawer-open`), so these must be handled manually in CSS with media queries.
- **Static files**: Django's `collectstatic` runs on app startup (`collect_static()` in alive). Static assets from alive are collected into `staticfiles/`.
- **Session & context**: `PlayerContextMiddleware` tracks current player, game, role (PLAYER/KEEPER), and character. Context vars like `current_game_id` scope ORM queries.

### Directory layout

```
app.py              # Starlette/PyView entry point
settings.py         # Django settings (SQLite, installed apps)
urls.py             # Django URL config (admin)
cards/              # Domain app
  models/           # Django models (Game, Player, Character, Card, Situation, HexMap, etc.)
  visibility.py     # Role-based visibility rules
  context.py        # Context variables (game_id, player_id)
  admin.py          # Django admin registration
staticfiles/        # Static assets (admin + alive JS/CSS)
```

## Setup

```bash
# Install dependencies
uv sync

# Run migrations
PYTHONPATH=. DJANGO_SETTINGS_MODULE=settings uv run django-admin migrate

# Create a superuser (optional, for admin access)
PYTHONPATH=. DJANGO_SETTINGS_MODULE=settings uv run django-admin createsuperuser
```

## Running the app

```bash
uv run python app.py
```

The app will be available at http://localhost:8001

- Alive UI: http://localhost:8001/alive/
- Django Admin: http://localhost:8001/admin/
