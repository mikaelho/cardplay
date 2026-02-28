from django.db import models
from alive import AliveMixin, AliveConf
from cards.visibility import game_visible, filter_games


class Game(models.Model, AliveMixin):
    """A single ongoing game, referring to a template."""

    alive = AliveConf(
        fields=("name", "template"),
        editable_fields=("name", "template"),
        visible_to=game_visible,
        filter_queryset=filter_games,
    )

    name = models.CharField(max_length=100)
    template = models.ForeignKey(
        "GameTemplate",
        on_delete=models.PROTECT,
        related_name="games",
    )
    game_time = models.JSONField(default=dict, blank=True)
    spare_die = models.PositiveSmallIntegerField(null=True, blank=True, default=None)

    def __str__(self):
        return self.name


SEASONS = ["spring", "harvest", "winter"]
SHIFTS = ["morning", "afternoon", "night"]


def advance_shift(current_time):
    """Return new time dict with shift advanced by one.
    Night→morning rolls day+1. Winter→spring also rolls year+1."""
    t = {**current_time} if current_time else {
        "age": "", "year": 1, "season": "spring", "day": 1, "shift": "morning",
    }
    idx = SHIFTS.index(t.get("shift", "morning"))
    if idx + 1 < len(SHIFTS):
        t["shift"] = SHIFTS[idx + 1]
    else:
        t["shift"] = SHIFTS[0]
        t["day"] = t.get("day", 1) + 1
    return t


def next_season(current_time):
    """Advance season by one. Winter→spring also advances year."""
    t = {**current_time}
    idx = SEASONS.index(t.get("season", "spring"))
    if idx + 1 < len(SEASONS):
        t["season"] = SEASONS[idx + 1]
    else:
        t["season"] = SEASONS[0]
        t["year"] = t.get("year", 1) + 1
    t["day"] = 1
    return t


def format_time(t):
    """Format time dict for display, e.g. 'Spring, Day 3, Afternoon'."""
    if not t:
        return ""
    parts = []
    if t.get("age"):
        parts.append(t["age"])
    if t.get("year"):
        parts.append(f"Year {t['year']}")
    if t.get("season"):
        parts.append(t["season"].title())
    if t.get("day"):
        parts.append(f"Day {t['day']}")
    if t.get("shift"):
        parts.append(t["shift"].title())
    return ", ".join(parts)


def time_group_key(t):
    """Return grouping key for timeline separators (everything except shift)."""
    if not t:
        return ""
    parts = []
    if t.get("age"):
        parts.append(t["age"])
    if t.get("year"):
        parts.append(f"Year {t['year']}")
    if t.get("season"):
        parts.append(t["season"].title())
    if t.get("day"):
        parts.append(f"Day {t['day']}")
    return ", ".join(parts)
