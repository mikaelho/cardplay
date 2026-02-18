from django.db import models
from alive import AliveMixin, AliveConf
from alive.conf import TagFieldConf
from cards.visibility import superuser_only


class GameTemplate(models.Model, AliveMixin):
    """Defines features of a game."""

    alive = AliveConf(
        fields=("name",),
        editable_fields=("name",),
        tag_fields=(
            TagFieldConf(field_name="tags"),
        ),
        visible_to=superuser_only,
    )

    name = models.CharField(max_length=100)
    tags = models.ManyToManyField(
        "Tag",
        blank=True,
        related_name="game_templates",
    )

    def __str__(self):
        return self.name
