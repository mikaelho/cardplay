from django.db import models
from alive import AliveMixin, AliveConf
from cards.visibility import superuser_only


class Player(models.Model, AliveMixin):
    """A player who can participate in multiple games."""

    alive = AliveConf(
        fields=("name", "superuser"),
        editable_fields=("name", "superuser"),
        visible_to=superuser_only,
    )

    name = models.CharField(max_length=100)
    superuser = models.BooleanField(default=False)

    def __str__(self):
        return self.name
