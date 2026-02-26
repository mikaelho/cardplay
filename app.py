"""Main entry point for the cardplay application."""

import os
import sys
from pathlib import Path

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Initialize Django BEFORE importing models
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings')
import django
django.setup()

from asgiref.sync import sync_to_async
from pyview import PyView
from pyview.template import RootTemplateContext
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import RedirectResponse
from starlette.routing import Route
from starlette.staticfiles import StaticFiles
from starlette.middleware.wsgi import WSGIMiddleware
from django.core.wsgi import get_wsgi_application
import uvicorn

import settings as django_settings
from alive import setup_alive, set_event_loop, get_registered_models, render_theme_picker, render_theme_script, collect_static, static_url
from cards.models import Player, Game, GameMembership, Character
from cards.context import current_game_id
from cards.sparks_view import create_sparks_liveview

# Cached player list for the selector dropdown
_player_options_cache = None


def _load_player_options_sync():
    """Load all players from DB (must be called from sync context)."""
    global _player_options_cache
    _player_options_cache = list(Player.objects.all().order_by("name").values("pk", "name"))


SUPERUSER_SENTINEL = "super"


class PlayerContextMiddleware:
    """ASGI middleware that sets contextvars needed by filter functions."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] in ("http", "websocket"):
            # Lazy-load player options cache on first HTTP request
            if _player_options_cache is None:
                await sync_to_async(_load_player_options_sync, thread_sensitive=False)()

            session = scope.get("session", {})
            t1 = current_game_id.set(session.get("game_id"))
            try:
                await self.app(scope, receive, send)
            finally:
                current_game_id.reset(t1)
        else:
            await self.app(scope, receive, send)


async def _compute_role_and_character(session):
    """Compute player_role and character_id for the current player/game selection."""
    player_id = session.get("player_id")
    game_id = session.get("game_id")

    if not player_id or player_id == SUPERUSER_SENTINEL or not game_id:
        session["player_role"] = None
        session["character_id"] = None
        return

    @sync_to_async(thread_sensitive=False)
    def _compute():
        try:
            membership = GameMembership.objects.get(player_id=player_id, game_id=game_id)
            role = membership.role
        except GameMembership.DoesNotExist:
            return None, None
        char_id = Character.objects.filter(
            player_id=player_id, game_id=game_id
        ).values_list('pk', flat=True).first()
        return role, char_id

    role, char_id = await _compute()
    session["player_role"] = role
    session["character_id"] = char_id


async def set_player(request):
    """Endpoint to set the current player in session."""
    player_id = request.query_params.get("id", "")
    referer = request.headers.get("referer", "/alive/")

    if player_id == SUPERUSER_SENTINEL:
        # Dev/testing superuser override — sees everything
        request.session["player_id"] = SUPERUSER_SENTINEL
        request.session["player_name"] = "Superuser"
        request.session["player_superuser"] = True
        request.session["visible_urls"] = [m["url"] for m in get_registered_models()]

        # Superuser sees all games
        @sync_to_async(thread_sensitive=False)
        def _all_games():
            return list(Game.objects.order_by("name").values("pk", "name"))

        games = await _all_games()
        request.session["game_options"] = games
        request.session["game_id"] = games[0]["pk"] if games else None
        request.session["player_role"] = None
        request.session["character_id"] = None
    elif player_id:
        try:
            player = await sync_to_async(Player.objects.get, thread_sensitive=False)(pk=int(player_id))
            request.session["player_id"] = player.pk
            request.session["player_name"] = player.name
            request.session["player_superuser"] = player.superuser

            # Precompute visible model URLs for sidebar filtering
            @sync_to_async(thread_sensitive=False)
            def _compute_visible():
                urls = []
                for m in get_registered_models():
                    model_cls = m.get("_model")
                    if model_cls:
                        c = model_cls.get_alive_conf()
                        if c.visible_to is not None and not c.visible_to(player.pk):
                            continue
                    urls.append(m["url"])
                return urls

            request.session["visible_urls"] = await _compute_visible()

            # Compute games for this player
            @sync_to_async(thread_sensitive=False)
            def _player_games():
                return list(
                    Game.objects.filter(memberships__player_id=player.pk)
                    .order_by("name").values("pk", "name")
                )

            games = await _player_games()
            request.session["game_options"] = games
            request.session["game_id"] = games[0]["pk"] if games else None
            await _compute_role_and_character(request.session)
        except Player.DoesNotExist:
            pass
    else:
        for key in ("player_id", "player_name", "player_superuser", "visible_urls",
                     "game_id", "game_options", "player_role", "character_id"):
            request.session.pop(key, None)

    # Refresh player cache in case players were added/removed
    await sync_to_async(_load_player_options_sync, thread_sensitive=False)()

    return RedirectResponse(url=referer, status_code=303)


async def set_game(request):
    """Endpoint to set the current game in session."""
    game_id = request.query_params.get("id", "")
    referer = request.headers.get("referer", "/alive/")

    if game_id:
        try:
            request.session["game_id"] = int(game_id)
        except (ValueError, TypeError):
            pass
    else:
        request.session.pop("game_id", None)

    await _compute_role_and_character(request.session)

    return RedirectResponse(url=referer, status_code=303)


async def get_frame_context(session):
    """Provide frame data for alive's LiveView templates."""
    player_id = session.get("player_id")
    visible_urls = session.get("visible_urls")

    # Build sidebar models filtered by player visibility
    if player_id is None:
        sidebar = []
    elif visible_urls is not None:
        sidebar = [m for m in get_registered_models() if m["url"] in visible_urls]
    else:
        sidebar = get_registered_models()

    # Build player options with Superuser entry
    players = _player_options_cache or []
    player_options = [{"pk": SUPERUSER_SENTINEL, "name": "Superuser"}] + list(players)

    # Game selector visibility
    game_options = session.get("game_options") or []
    show_game_selector = len(game_options) > 1

    sidebar_items = [{"url": m["url"], "title": m["title"]} for m in sidebar]

    # Add keeper-only pages
    is_keeper = session.get("player_role") == "keeper" or session.get("player_superuser")
    if is_keeper:
        sidebar_items.append({"url": "/alive/sparks/", "title": "Sparks"})

    return {
        "app_title": "Cardplay",
        "app_url": "/alive/",
        "set_player_url": "/set-player?id=",
        "set_game_url": "/set-game?id=",
        "player_options": player_options,
        "player_id": player_id,
        "game_options": game_options,
        "game_id": session.get("game_id"),
        "show_game_selector": show_game_selector,
        "sidebar_models": sidebar_items,
        "theme_picker_html": render_theme_picker(),
    }


def custom_root_template(context: RootTemplateContext) -> str:
    """Minimal root template — frame is rendered inside LiveView templates."""
    suffix = " | Cardplay"
    title = context.get("title") or "Cardplay"
    render_title = (title + suffix) if title else "Cardplay"

    additional_head_elements = "\n".join(context["additional_head_elements"])
    theme_script = render_theme_script("cardplay-theme")

    return f"""<!DOCTYPE html>
<html lang="en" data-theme="light">
    <head>
      <title data-suffix="{suffix}">{render_title}</title>
      <meta name="csrf-token" content="{context["csrf_token"]}" />
      <meta charset="utf-8">
      <meta http-equiv="X-UA-Compatible" content="IE=edge">
      <meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no">
      <link href="https://cdn.jsdelivr.net/npm/daisyui@5" rel="stylesheet" type="text/css" />
      <link href="https://cdn.jsdelivr.net/npm/daisyui@5/themes.css" rel="stylesheet" type="text/css" />
      <script src="https://cdn.jsdelivr.net/npm/@tailwindcss/browser@4"></script>
      <link rel="stylesheet" href="{static_url('/django-static/alive/css/alive.css')}">
      <style>
        /* Responsive drawer: DaisyUI drawer-open via media query
           (Tailwind v4 browser build can't generate responsive variants of DaisyUI classes) */
        @media (min-width: 1024px) {{
            .drawer > .drawer-toggle {{ display: none !important; }}
            .drawer > .drawer-toggle ~ .drawer-side {{
                pointer-events: auto !important;
                visibility: visible !important;
                overscroll-behavior: auto !important;
                opacity: 1 !important;
                width: auto !important;
                display: block !important;
                position: sticky !important;
                overflow-y: auto !important;
            }}
            .drawer > .drawer-toggle ~ .drawer-side > .drawer-overlay {{
                cursor: default !important;
                background-color: transparent !important;
            }}
            .drawer > .drawer-toggle ~ .drawer-side > :not(.drawer-overlay) {{
                translate: 0% !important;
            }}
        }}
      </style>
      <script src="https://cdn.jsdelivr.net/npm/sortablejs@1.15.2/Sortable.min.js"></script>
      <script src="{static_url('/django-static/alive/js/dragdrop.js')}"></script>
      <script src="{static_url('/django-static/alive/js/keyboard.js')}"></script>
      <script src="{static_url('/django-static/alive/js/hexmap.js')}"></script>
      <script defer type="text/javascript" src="/static/assets/app.js"></script>
      {additional_head_elements}
    </head>
    <body class="bg-base-200 min-h-screen">
      <div
        data-phx-main="true"
        data-phx-session="{context["session"]}"
        data-phx-static=""
        id="phx-{context["id"]}"
        >
        {context["content"]}
      </div>
      {theme_script}
    </body>
</html>
"""


def create_app():
    """Create and configure the PyView application."""
    import asyncio
    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def lifespan(app):
        loop = asyncio.get_running_loop()
        set_event_loop(loop)
        yield

    app = PyView(lifespan=lifespan)
    app.rootTemplate = custom_root_template

    # Collect static files before mounting
    collect_static()

    # Mount PyView's static assets
    app.mount("/static", StaticFiles(packages=[("pyview", "static")]), name="static")

    # Mount Django static files
    app.mount("/django-static", StaticFiles(directory="staticfiles"), name="django-static")

    # Mount Django admin
    django_wsgi_app = get_wsgi_application()
    app.mount("/admin", WSGIMiddleware(django_wsgi_app))

    # Add player and game selection endpoints
    app.routes.insert(0, Route("/set-player", set_player))
    app.routes.insert(1, Route("/set-game", set_game))

    # Setup Alive with frame context provider
    setup_alive(app, url_prefix="/alive", frame_context_provider=get_frame_context)

    # Register Sparks & Inspirations page (keeper-only)
    sparks_view = create_sparks_liveview()
    app.add_live_view("/alive/sparks/", sparks_view)

    # Add middleware (order matters: last added wraps outermost)
    # PlayerContextMiddleware must be inside SessionMiddleware
    app.add_middleware(PlayerContextMiddleware)
    app.add_middleware(SessionMiddleware, secret_key=django_settings.SECRET_KEY)

    return app


app = create_app()


if __name__ == "__main__":
    import alive
    alive_dir = str(Path(alive.__file__).resolve().parent)
    uvicorn.run("app:app", host="0.0.0.0", port=8001, reload=True, reload_dirs=[".", alive_dir])
