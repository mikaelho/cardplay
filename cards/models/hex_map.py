from django.db import models
from alive import AliveMixin, AliveConf
from cards.visibility import character_visible, filter_maps


class HexMap(models.Model, AliveMixin):
    """A hex map for a game."""

    alive = AliveConf(
        fields=("name",),
        editable_fields=("name",),
        template="map.html",
        visible_to=character_visible,
        filter_queryset=filter_maps,
    )

    name = models.CharField(max_length=200)
    game = models.ForeignKey(
        "Game",
        on_delete=models.CASCADE,
        related_name="maps",
    )
    hexes = models.JSONField(default=dict, blank=True)  # {"col,row": "symbol_id", ...}
    rivers = models.JSONField(default=list, blank=True)  # [["col,row", ...], ...]
    overlays = models.JSONField(default=dict, blank=True)  # {"col,row": "overlay_id", ...}
    barriers = models.JSONField(default=dict, blank=True)  # {"col,row": [edge_indices], ...}
    revealed_overlays = models.JSONField(default=dict, blank=True)  # {"col,row": "overlay_id", ...} overlays visible to players
    notes = models.JSONField(default=dict, blank=True)  # {"col,row": "markdown text", ...}
    site_maps = models.JSONField(default=dict, blank=True)  # {"col,row": {"nodes": {...}, "routes": [...], "entrances": [...]}}
    party_location = models.CharField(max_length=20, blank=True)  # "col,row"
    party_trail = models.JSONField(default=list, blank=True)  # ["col,row", ...] recent past locations

    def __str__(self):
        return self.name
