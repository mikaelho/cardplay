from django.db import models
from alive import AliveMixin, AliveConf


"""
A card can have bands of bad, fair and good outcomes as values from 1-6.

Bands are defined below, in the order bad, fair, good.

Default (neutral) band is 4, anything below that is a disadvantage, and above an advantage.
"""

bands = {
    10: "114",
    9: "123",
    8: "132",
    7: "141",
    6: "213",
    5: "222",
    4: "231",
    3: "312",
    2: "321",
    1: "411",
}

band_labels = ("Bad", "So-so", "Good")


def get_bands_for_level(level: int) -> list[dict]:
    """Return band breakdown for a level, Good first, with aligned dice ranges."""
    band_str = bands.get(level, "231")  # default to level 4
    result = []
    face = 1
    for i in range(3):
        count = int(band_str[i])
        if count == 0:
            continue
        end = face + count - 1
        if count == 1:
            dice_range = f" {face} "
        else:
            dice_range = f"{face}-{end}"
        result.append({
            "label": band_labels[i],
            "count": count,
            "dice_range": dice_range,
        })
        face = end + 1
    result.reverse()  # Good at top
    return result


def get_band_for_die(level: int, die_value: int) -> str | None:
    """Return which band label a die value falls into for a given level."""
    band_str = bands.get(level, "231")
    face = 1
    for i in range(3):
        count = int(band_str[i])
        if count == 0:
            face += count
            continue
        end = face + count - 1
        if face <= die_value <= end:
            return band_labels[i]
        face = end + 1
    return None


success_bands = {  # Total fail is impossible, can be inverted for total fails, not sure if these will be used
    4: "015",
    3: "024",
    2: "033",
    1: "042",
    0: "051",
}

from cards.visibility import card_visible, filter_cards


class Card(models.Model, AliveMixin):
    """A single playable card that can be attached to multiple players."""

    alive = AliveConf(
        fields=("name", "notes"),
        editable_fields=("name", "notes"),
        visible_to=card_visible,
        filter_queryset=filter_cards,
    )

    name = models.CharField(max_length=200)
    notes = models.TextField(blank=True)
    characters = models.ManyToManyField(
        "Character",
        through="CharacterCard",
        blank=True,
        related_name="cards",
    )

    def __str__(self):
        return self.name
