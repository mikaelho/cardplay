from django.db import models


class Timeline(models.Model):
    """A game's shared timeline: a title, notes, and the cards placed on it.

    One per game (created on demand). Not an AliveMixin model — it has no CRUD
    list of its own; it is edited through the timeline page alongside its cards.
    """

    game = models.OneToOneField(
        "Game",
        on_delete=models.CASCADE,
        related_name="timeline",
    )
    title = models.CharField(max_length=200, blank=True)
    notes = models.TextField(blank=True)

    def __str__(self):
        return self.title or f"Timeline for game {self.game_id}"
