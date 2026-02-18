"""Contextvars for passing game/player context to views and filter functions."""

import contextvars

current_game_id = contextvars.ContextVar('current_game_id', default=None)
current_game_options = contextvars.ContextVar('current_game_options', default=None)
current_player_role = contextvars.ContextVar('current_player_role', default=None)
current_character_id = contextvars.ContextVar('current_character_id', default=None)
