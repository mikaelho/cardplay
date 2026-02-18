from django.db import models
from alive import AliveMixin, AliveConf
from cards.visibility import superuser_only


class Hand(models.Model, AliveMixin):
    """A hand of cards held by a character."""

    alive = AliveConf(
        fields=("name", "character"),
        editable_fields=("name", "character"),
        visible_to=superuser_only,
    )

    name = models.CharField(max_length=100)
    character = models.ForeignKey(
        "Character",
        on_delete=models.CASCADE,
        related_name="hands",
    )
    cards = models.ManyToManyField(
        "CharacterCard",
        blank=True,
        related_name="hands",
    )

    def __str__(self):
        return self.name
