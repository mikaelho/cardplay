from django.db import models
from alive import AliveMixin, AliveConf
from cards.visibility import character_visible, filter_characters


class Character(models.Model, AliveMixin):
    """A character with a name, a player, and a sheet."""

    alive = AliveConf(
        fields=("name", "callsign", "player", "notes"),
        editable_fields=("name", "callsign", "player", "notes"),
        create_fields=("name", "callsign", "game", "player", "sheet"),
        list_fields=("name", "callsign", "player"),
        compact_fields=("callsign", "player"),
        inline=("character_cards",),
        visible_to=character_visible,
        filter_queryset=filter_characters,
    )

    name = models.CharField(max_length=100)
    callsign = models.CharField(max_length=100, blank=True)
    game = models.ForeignKey(
        "Game",
        on_delete=models.CASCADE,
        related_name="characters",
    )
    player = models.ForeignKey(
        "Player",
        on_delete=models.CASCADE,
        related_name="characters",
    )
    sheet = models.ForeignKey(
        "Sheet",
        on_delete=models.PROTECT,
        related_name="characters",
    )
    notes = models.TextField(blank=True)

    def __str__(self):
        return self.name
