from django.db import models
from alive import AliveMixin, AliveConf
from cards.visibility import card_visible, filter_situations


class KeeperNote(models.Model, AliveMixin):
    """General keeper notes, not tied to a specific hex location."""

    alive = AliveConf(
        fields=("name", "notes"),
        editable_fields=("name", "notes"),
        create_fields=("name", "game"),
        list_fields=("name", "notes"),
        visible_to=card_visible,
        filter_queryset=filter_situations,
    )

    name = models.CharField(max_length=200)
    notes = models.TextField(blank=True)
    game = models.ForeignKey(
        "Game",
        on_delete=models.CASCADE,
        related_name="keeper_notes",
    )

    def __str__(self):
        return self.name
