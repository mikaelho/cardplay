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
- **alive package**: Installed as an editable sibling (`../alive`). Provides generic CRUD UI generation, `AliveMixin`/`AliveConf` for model configuration, visibility filtering, drag-drop support, and JS hooks. Alive is a generic framework — all cardplay-specific behavior lives in this repo via hooks.
- **cards app**: Contains all domain models and logic specific to playing card-based RPGs — games, players, characters, cards, hands, situations, hex maps, sheets/tags, and visibility rules (`cards/visibility.py`).
- **cards/alive_hooks.py**: All cardplay-specific LiveView behavior — event handlers, mount/refresh/params hooks, situation/map/hand data loading. Registered on `AliveConf` instances in `register_hooks()`.
- **cards/ui.py**: Cardplay-specific UI rendering — dice SVGs, ratings, hex map rendering, site map rendering.
- **templates/**: Cardplay-specific templates (map, situation, hand footer, search) and frame overrides (frame_top with player/game selectors, frame_bottom with dice and sidebar). These override alive's generic templates via `template_dirs`.
- **Frontend**: Tailwind CSS v4 (browser build) + DaisyUI 5 (CDN). Custom JS hooks in `static/cards/js/` (hexmap) and alive's `static/alive/js/` (drag-drop, keyboard shortcuts). Note: Tailwind v4 browser build cannot generate responsive variants of DaisyUI component classes (e.g. `lg:drawer-open`), so these must be handled manually in CSS with media queries.
- **Static files**: Django's `collectstatic` runs on app startup (`collect_static()` in alive). Static assets from alive and `static/` are collected into `staticfiles/`.
- **Session & context**: `PlayerContextMiddleware` tracks current player, game, role (PLAYER/KEEPER), and character. Context vars like `current_game_id` scope ORM queries.

### Directory layout

```
app.py              # Starlette/PyView entry point
settings.py         # Django settings (SQLite, installed apps)
urls.py             # Django URL config (admin)
cards/              # Domain app
  models/           # Django models (Game, Player, Character, Card, Situation, HexMap, etc.)
  alive_hooks.py    # All cardplay-specific LiveView behavior (hooks registered on AliveConf)
  ui.py             # Cardplay UI rendering (dice, ratings, hex maps, site maps)
  sparks_view.py    # Standalone Sparks & Inspirations LiveView page
  visibility.py     # Role-based visibility rules
  context.py        # Context variables (game_id, player_id)
  admin.py          # Django admin registration
templates/          # Cardplay templates (overrides alive defaults)
static/cards/js/    # Cardplay JS (hexmap.js)
staticfiles/        # Collected static assets (admin + alive + cards)
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
