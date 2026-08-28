from django.db import models
from alive import AliveMixin, AliveConf
from cards.visibility import character_visible, filter_timeline_cards


class TimelineCard(models.Model, AliveMixin):
    """A note card on a game's shared timeline.

    Top-level cards (depth 0) sit in a horizontal line of slots, gaps allowed.
    Detail cards hang beneath a parent, up to two levels deep (depth 1 and 2).
    Layout is derived from the parent relationship, so moving a card carries
    its whole detail subtree along.
    """

    alive = AliveConf(
        fields=("title", "notes"),
        editable_fields=("title", "notes"),
        template="timeline.html",
        visible_to=character_visible,
        filter_queryset=filter_timeline_cards,
    )

    timeline = models.ForeignKey(
        "Timeline",
        on_delete=models.CASCADE,
        related_name="cards",
    )
    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="children",
    )
    depth = models.PositiveSmallIntegerField(default=0)  # 0 timeline, 1 detail, 2 sub-detail
    position = models.IntegerField(default=0)  # slot index (depth 0) or sibling order (depth 1/2)
    title = models.CharField(max_length=200, blank=True)
    notes = models.TextField(blank=True)
    tint = models.CharField(max_length=20, blank=True)  # CSS colour, blank = no tint

    class Meta:
        verbose_name = "Timeline"
        verbose_name_plural = "Timeline"
        ordering = ["position", "pk"]

    def __str__(self):
        return self.title or f"Card {self.pk}"
