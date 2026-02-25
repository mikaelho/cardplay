"""Contextvars for passing game/player context to views and filter functions."""

import contextvars

current_game_id = contextvars.ContextVar('current_game_id', default=None)
