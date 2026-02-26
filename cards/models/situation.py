from django.db import models
from alive import AliveMixin, AliveConf
from cards.visibility import card_visible, filter_situations

SITUATION_TYPE_CHOICES = [
    ("situation", "Situation"),
    ("note", "Note"),
]


class Situation(models.Model, AliveMixin):
    """A scene or encounter involving cards from any character in the game."""

    alive = AliveConf(
        fields=("name", "notes"),
        editable_fields=("name", "notes"),
        create_fields=("name", "game"),
        template="situation.html",
        visible_to=card_visible,
        filter_queryset=filter_situations,
    )

    name = models.CharField(max_length=200)
    notes = models.TextField(blank=True)
    game = models.ForeignKey(
        "Game",
        on_delete=models.CASCADE,
        related_name="situations",
    )
    cards = models.ManyToManyField(
        "CharacterCard",
        blank=True,
        related_name="situations",
    )
    dice = models.JSONField(default=list, blank=True)
    assignments = models.JSONField(default=dict, blank=True)
    dice_assigned = models.BooleanField(default=False)
    resolved = models.BooleanField(default=False)
    situation_type = models.CharField(
        max_length=20,
        choices=SITUATION_TYPE_CHOICES,
        default="situation",
    )
    location = models.CharField(max_length=20, blank=True)
    game_time = models.JSONField(default=dict, blank=True)

    def __str__(self):
        return self.name
