from django.db import models
from alive import AliveMixin, AliveConf
from cards.visibility import superuser_only


class Tag(models.Model, AliveMixin):
    """A tag that can be associated with game templates and sheets."""

    alive = AliveConf(
        fields=("name",),
        editable_fields=("name",),
        visible_to=superuser_only,
    )

    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name
