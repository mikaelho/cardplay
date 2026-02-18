from django.db import models
from alive import AliveMixin, AliveConf
from alive.conf import TagFieldConf
from cards.visibility import superuser_only


class CharacterCard(models.Model, AliveMixin):
    """A character's connection to a card, with their specific level."""

    alive = AliveConf(
        fields=("character", "card", "level"),
        editable_fields=("character", "card", "level"),
        tag_fields=(
            TagFieldConf(field_name="tag", scope_path="character__sheet"),
        ),
        visible_to=superuser_only,
    )

    character = models.ForeignKey(
        "Character",
        on_delete=models.CASCADE,
        related_name="character_cards",
    )
    card = models.ForeignKey(
        "Card",
        on_delete=models.CASCADE,
        related_name="character_cards",
    )
    level = models.PositiveSmallIntegerField(default=4)
    tag = models.ForeignKey(
        "Tag",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="character_cards",
    )

    class Meta:
        unique_together = [["character", "card"]]

    def __str__(self):
        return f"{self.character} - {self.card} (level {self.level})"

    @classmethod
    def get_inline_display_data(cls, item_data: dict) -> dict:
        """Compute extra display data for inline rendering."""
        from .card import get_bands_for_level
        from alive.ui import render_rating
        level = item_data["through_fields"].get("level", 4)
        if isinstance(level, str):
            level = int(level) if level else 4
        return {
            "bands": get_bands_for_level(level),
            "rating_html": render_rating(level),
            "level": level,
        }

    @classmethod
    def get_inline_groups(cls, items: list[dict], **kwargs) -> list[dict]:
        """Group inline items by tag, ordered by sheet tag position."""
        parent = kwargs.get('parent_item')

        # Get tag order from the character's sheet
        tag_order = None
        if parent and hasattr(parent, 'sheet_id') and parent.sheet_id:
            from cards.models.sheet_tag import SheetTag
            tag_order = list(
                SheetTag.objects.filter(sheet_id=parent.sheet_id)
                .order_by('position')
                .values_list('tag__name', flat=True)
            )

        # Group items by tag
        groups = {}
        for item in items:
            tag = item.get("through_fields", {}).get("tag") or ""
            groups.setdefault(tag, []).append(item)

        # Order groups by sheet tag order if available
        result = []
        if tag_order:
            for tag_name in tag_order:
                if tag_name in groups:
                    result.append({"label": tag_name, "related_items": groups.pop(tag_name)})
        # Append any remaining groups not in the tag order
        for tag_name, tag_items in groups.items():
            result.append({"label": tag_name, "related_items": tag_items})
        return result
