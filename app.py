"""Main entry point for the cardplay application."""

import contextvars
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
from cards.context import current_game_id, current_game_options, current_player_role, current_character_id

# Context vars for passing session data to the sync root template
_current_player_id = contextvars.ContextVar('current_player_id', default=None)
_current_player_name = contextvars.ContextVar('current_player_name', default=None)
_current_visible_urls = contextvars.ContextVar('current_visible_urls', default=None)

# Cached player list for the selector dropdown
_player_options_cache = None


def _load_player_options_sync():
    """Load all players from DB (must be called from sync context)."""
    global _player_options_cache
    _player_options_cache = list(Player.objects.all().order_by("name").values("pk", "name"))


SUPERUSER_SENTINEL = "super"


def _render_player_selector(current_player_id):
    """Render player selector dropdown HTML using cached player list."""
    players = _player_options_cache or []
    options = ['<option value="">-- Select Player --</option>']
    super_selected = 'selected' if current_player_id == SUPERUSER_SENTINEL else ''
    options.append(f'<option value="{SUPERUSER_SENTINEL}" {super_selected}>Superuser</option>')
    for p in players:
        selected = 'selected' if p["pk"] == current_player_id else ''
        options.append(f'<option value="{p["pk"]}" {selected}>{p["name"]}</option>')
    return f'''<select class="select select-sm select-bordered"
        onchange="window.location.href='/set-player?id=' + this.value">
        {"".join(options)}
    </select>'''


class PlayerContextMiddleware:
    """ASGI middleware that copies player session data into contextvars."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] in ("http", "websocket"):
            # Lazy-load player options cache on first HTTP request
            if _player_options_cache is None:
                await sync_to_async(_load_player_options_sync, thread_sensitive=False)()

            session = scope.get("session", {})
            t1 = _current_player_id.set(session.get("player_id"))
            t2 = _current_player_name.set(session.get("player_name"))
            t3 = _current_visible_urls.set(session.get("visible_urls"))
            t4 = current_game_id.set(session.get("game_id"))
            t5 = current_game_options.set(session.get("game_options"))
            t6 = current_player_role.set(session.get("player_role"))
            t7 = current_character_id.set(session.get("character_id"))
            try:
                await self.app(scope, receive, send)
            finally:
                _current_player_id.reset(t1)
                _current_player_name.reset(t2)
                _current_visible_urls.reset(t3)
                current_game_id.reset(t4)
                current_game_options.reset(t5)
                current_player_role.reset(t6)
                current_character_id.reset(t7)
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


def _render_game_selector(game_id_value):
    """Render game selector dropdown HTML using game options from contextvar."""
    game_options = current_game_options.get()
    if not game_options or len(game_options) <= 1:
        return ''
    options = []
    for g in game_options:
        selected = 'selected' if g["pk"] == game_id_value else ''
        options.append(f'<option value="{g["pk"]}" {selected}>{g["name"]}</option>')
    return f'''<select class="select select-sm select-bordered"
        onchange="window.location.href='/set-game?id=' + this.value">
        {"".join(options)}
    </select>'''


def custom_root_template(context: RootTemplateContext) -> str:
    """Custom root template with drawer navigation."""
    suffix = " | Cardplay"
    title = context.get("title") or "Cardplay"
    render_title = (title + suffix) if title else "Cardplay"

    additional_head_elements = "\n".join(context["additional_head_elements"])

    # Build sidebar menu, filtered by player visibility
    player_id = _current_player_id.get()
    visible_urls = _current_visible_urls.get()
    if player_id is None:
        # No player selected - show no models
        models = []
    elif visible_urls is not None:
        models = [m for m in get_registered_models() if m["url"] in visible_urls]
    else:
        models = get_registered_models()
    sidebar_items = "\n".join([
        f'<li><a href="{m["url"]}">{m["title"]}</a></li>'
        for m in models
    ])

    # Player selector
    player_selector = _render_player_selector(player_id)

    # Game selector
    game_id_value = current_game_id.get()
    game_selector = _render_game_selector(game_id_value)

    # Bottom padding for hand footer
    player_role = current_player_role.get()
    character_id = current_character_id.get()
    footer_padding = "pb-28" if player_role == "player" and character_id else ""

    main_content = f"""
      <div
        data-phx-main="true"
        data-phx-session="{context["session"]}"
        data-phx-static=""
        id="phx-{context["id"]}"
        >
        {context["content"]}
    </div>"""

    navbar = f"""
      <div class="navbar bg-base-100 shadow mb-4">
        <div class="flex-1">
          <label for="app-drawer" class="btn btn-ghost lg:hidden">
            <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16" />
            </svg>
          </label>
          <a href="/alive/" class="btn btn-ghost text-xl">Cardplay</a>
        </div>
        <div class="flex-none flex items-center gap-2">
          {player_selector}
          {game_selector}
          {render_theme_picker()}
        </div>
      </div>
    """

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
      <script src="https://cdn.jsdelivr.net/npm/sortablejs@1.15.2/Sortable.min.js"></script>
      <script src="{static_url('/django-static/alive/js/dragdrop.js')}"></script>
      <script src="{static_url('/django-static/alive/js/keyboard.js')}"></script>
      <script defer type="text/javascript" src="/static/assets/app.js"></script>
      {additional_head_elements}
    </head>
    <body class="bg-base-200 min-h-screen">
      <div class="drawer lg:drawer-open">
        <input id="app-drawer" type="checkbox" class="drawer-toggle" />
        <div class="drawer-content {footer_padding}">
          {navbar}
          {main_content}
        </div>
        <div class="drawer-side">
          <label for="app-drawer" aria-label="close sidebar" class="drawer-overlay"></label>
          <ul class="menu bg-base-100 min-h-full w-64 p-4">
            <li class="menu-title">Models</li>
            {sidebar_items}
          </ul>
        </div>
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

    # Setup Alive
    setup_alive(app, url_prefix="/alive")

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
