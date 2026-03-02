from django.db import models
from alive import AliveMixin, AliveConf
from cards.visibility import superuser_only


class SheetDefaultCard(models.Model, AliveMixin):
    """A default card template on a Sheet, created on new characters."""

    alive = AliveConf(
        fields=("name", "notes", "tag", "sheet"),
        editable_fields=("name", "notes", "tag"),
        create_fields=("name", "notes", "tag", "sheet"),
        visible_to=superuser_only,
    )

    sheet = models.ForeignKey(
        "Sheet",
        on_delete=models.CASCADE,
        related_name="default_cards",
    )
    name = models.CharField(max_length=200)
    notes = models.TextField(blank=True, default="")
    tag = models.ForeignKey(
        "Tag",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    def __str__(self):
        return self.name
