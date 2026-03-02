from django.db import models
from alive import AliveMixin, AliveConf
from alive.conf import TagFieldConf
from cards.visibility import superuser_only


class Sheet(models.Model, AliveMixin):
    """A sheet belonging to a game template, with available tags."""

    alive = AliveConf(
        fields=("name", "notes", "template"),
        editable_fields=("name", "notes", "template"),
        tag_fields=(
            TagFieldConf(field_name="tags", scope_path="template"),
        ),
        visible_to=superuser_only,
        dive_to=("default_cards",),
    )

    name = models.CharField(max_length=100)
    notes = models.TextField(blank=True, default="")
    template = models.ForeignKey(
        "GameTemplate",
        on_delete=models.CASCADE,
        related_name="sheets",
    )
    tags = models.ManyToManyField(
        "Tag",
        blank=True,
        related_name="sheets",
        through="SheetTag",
    )

    def __str__(self):
        return self.name
