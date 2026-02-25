from django.db import models


class SituationCard(models.Model):
    """An archived snapshot of a card used in a rolled situation."""

    situation = models.ForeignKey(
        "Situation",
        on_delete=models.CASCADE,
        related_name="situation_cards",
    )
    name = models.CharField(max_length=200)
    notes = models.TextField(blank=True)
    level = models.PositiveSmallIntegerField(default=4)
    character_name = models.CharField(max_length=200, blank=True)
    used = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.name} ({self.character_name})"
