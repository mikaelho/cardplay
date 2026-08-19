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
    # Temporary shift away from the baseline level -- a short-term advantage
    # or disadvantage. Cleared by hand, never automatically.
    level_mod = models.SmallIntegerField(default=0)
    tag = models.ForeignKey(
        "Tag",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="character_cards",
    )

    class Meta:
        unique_together = [["character", "card"]]

    @property
    def effective_level(self) -> int:
        from .card import effective_level
        return effective_level(self.level, self.level_mod)

    def __str__(self):
        return f"{self.character} - {self.card} (level {self.level})"

    @classmethod
    def get_inline_extra_fields(cls, inline_info: dict) -> list[dict]:
        """Hide level_mod from the inline create form -- it is set with the
        situation card controls, not typed in when a card is added."""
        return [
            f for f in super().get_inline_extra_fields(inline_info)
            if f.get("name") != "level_mod"
        ]

    @classmethod
    def get_inline_display_data(cls, item_data: dict) -> dict:
        """Compute extra display data for inline rendering."""
        from .card import get_bands_for_level, effective_level
        from cards.ui import render_rating, render_level
        fields = item_data["through_fields"]
        level = fields.get("level", 4)
        if isinstance(level, str):
            level = int(level) if level else 4
        mod = fields.get("level_mod", 0)
        if isinstance(mod, str):
            mod = int(mod) if mod else 0
        current = effective_level(level, mod)
        return {
            "bands": get_bands_for_level(current),
            "rating_html": render_rating(current),
            # Rendered rather than a bare number so the baseline shows through
            # alive's generic inline level display.
            "level": render_level(level, mod),
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
