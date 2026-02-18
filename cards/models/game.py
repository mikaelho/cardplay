from django.db import models
from alive import AliveMixin, AliveConf
from cards.visibility import game_visible, filter_games


class Game(models.Model, AliveMixin):
    """A single ongoing game, referring to a template."""

    alive = AliveConf(
        fields=("name", "template"),
        editable_fields=("name", "template"),
        visible_to=game_visible,
        filter_queryset=filter_games,
    )

    name = models.CharField(max_length=100)
    template = models.ForeignKey(
        "GameTemplate",
        on_delete=models.PROTECT,
        related_name="games",
    )

    def __str__(self):
        return self.name
