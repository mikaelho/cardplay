"""Visibility rules for cardplay models."""

from cards.context import current_game_id

SUPERUSER_SENTINEL = "super"


def _get_player(player_id):
    """Resolve a Player instance from an ID. Returns None if not found."""
    if player_id is None or player_id == SUPERUSER_SENTINEL:
        return None
    from cards.models import Player
    try:
        return Player.objects.get(pk=player_id)
    except (Player.DoesNotExist, ValueError, TypeError):
        return None


def _is_superuser(player_id):
    """Check if a player_id corresponds to a superuser."""
    if player_id == SUPERUSER_SENTINEL:
        return True
    player = _get_player(player_id)
    return player is not None and player.superuser


# --- visible_to hooks ---

def superuser_only(player_id):
    """Only superusers can see this model."""
    return _is_superuser(player_id)


def game_visible(player_id):
    """All logged-in players can see games (filtered by membership)."""
    return player_id is not None


def character_visible(player_id):
    """All logged-in players can see characters (filtered by role)."""
    return player_id is not None


def card_visible(player_id):
    """Superusers and keepers see cards in sidebar; players see cards only inline on characters."""
    if _is_superuser(player_id):
        return True
    if player_id is None:
        return False
    from cards.models import GameMembership
    return GameMembership.objects.filter(
        player_id=player_id, role=GameMembership.Role.KEEPER
    ).exists()


# --- filter_queryset hooks ---

def filter_games(qs, player_id):
    """Superusers see all games; others see only games they're members of."""
    if _is_superuser(player_id):
        return qs
    if player_id is None:
        return qs.none()
    return qs.filter(memberships__player_id=player_id).distinct()


def filter_characters(qs, player_id):
    """
    Superusers see all characters.
    Keepers see all characters in their games.
    Players see only characters of other player-role members (not keeper characters).
    When a game is selected, further scopes to that game only.
    """
    if _is_superuser(player_id):
        game_id = current_game_id.get()
        if game_id:
            qs = qs.filter(game_id=game_id)
        return qs
    if player_id is None:
        return qs.none()

    from django.db.models import Q
    from cards.models import GameMembership

    roles = dict(
        GameMembership.objects.filter(player_id=player_id)
        .values_list("game_id", "role")
    )
    game_ids = set(roles.keys())

    # Scope by selected game if set
    game_id = current_game_id.get()
    if game_id:
        game_ids = game_ids & {game_id}

    qs = qs.filter(game_id__in=game_ids)

    # In games where I'm a player: hide keeper characters
    player_game_ids = [gid for gid, role in roles.items() if role == "player" and gid in game_ids]
    if player_game_ids:
        keeper_ids = set(
            GameMembership.objects.filter(
                game_id__in=player_game_ids, role="keeper"
            ).values_list("player_id", flat=True)
        )
        if keeper_ids:
            qs = qs.exclude(Q(game_id__in=player_game_ids) & Q(player_id__in=keeper_ids))

    return qs.distinct()


def filter_cards(qs, player_id):
    """Superusers see all cards; others see cards linked to characters in their games.
    When a game is selected, further scopes to that game only."""
    if _is_superuser(player_id):
        game_id = current_game_id.get()
        if game_id:
            qs = qs.filter(characters__game_id=game_id)
        return qs.distinct()
    if player_id is None:
        return qs.none()
    from cards.models import GameMembership
    game_ids = set(
        GameMembership.objects.filter(player_id=player_id)
        .values_list("game_id", flat=True)
    )
    game_id = current_game_id.get()
    if game_id:
        game_ids = game_ids & {game_id}
    return qs.filter(characters__game_id__in=game_ids).distinct()
