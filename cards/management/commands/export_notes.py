"""Export game notes (keeper notes, hex maps, characters & cards, situations)
to a tree of Markdown files for reading.

Re-runnable: the output directory is wiped and rebuilt on each run, so it always
reflects the current database.

    PYTHONPATH=. DJANGO_SETTINGS_MODULE=settings uv run django-admin export_notes
    PYTHONPATH=. DJANGO_SETTINGS_MODULE=settings uv run django-admin export_notes --output notes
"""

import shutil
from pathlib import Path

from django.core.management.base import BaseCommand
from django.utils.text import slugify

from cards.models import (
    Game,
    Character,
    CharacterCard,
    KeeperNote,
    TimelineCard,
)
from cards.models.hex_map import HexMap
from cards.models.situation import Situation
from cards.models.card import get_bands_for_level, effective_level, get_band_for_die
from cards.models.sheet_tag import SheetTag


def slug(name, fallback):
    s = slugify(name or "")
    return s or fallback


def unique_names(items, name_attr="name"):
    """Yield (item, slug) with duplicate slugs disambiguated by pk."""
    seen = {}
    for it in items:
        base = slug(getattr(it, name_attr, ""), f"item-{it.pk}")
        if base in seen:
            base = f"{base}-{it.pk}"
        seen[base] = True
        yield it, base


def bands_line(level):
    """One-line textual band breakdown, e.g. 'Good 4-6 / So-so 3 / Bad 1-2'."""
    parts = [f"{b['label']} {b['dice_range'].strip()}" for b in get_bands_for_level(level)]
    return " / ".join(parts)


def coord_key(cr):
    """Sort key for a 'col,row' string."""
    try:
        c, r = cr.split(",")
        return (int(c), int(r))
    except (ValueError, AttributeError):
        return (0, 0)


class Command(BaseCommand):
    help = "Export keeper notes, hex maps, characters and situations to Markdown."

    def add_arguments(self, parser):
        parser.add_argument(
            "--output",
            default="notes",
            help="Output directory (wiped and rebuilt each run). Default: notes",
        )

    def handle(self, *args, **opts):
        out = Path(opts["output"])
        if out.exists():
            shutil.rmtree(out)
        out.mkdir(parents=True, exist_ok=True)

        games = list(Game.objects.select_related("template").all())
        for game in games:
            gdir = out / slug(game.name, f"game-{game.pk}")
            gdir.mkdir(parents=True, exist_ok=True)
            self._write_game_readme(game, gdir)
            self._write_keeper_notes(game, gdir)
            self._write_timeline(game, gdir)
            self._write_characters(game, gdir)
            self._write_maps(game, gdir)
            self._write_situations(game, gdir)
            self.stdout.write(self.style.SUCCESS(f"Exported {game.name} -> {gdir}"))

        self.stdout.write(self.style.SUCCESS(f"Done. {len(games)} game(s) -> {out}/"))

    # -- game overview -----------------------------------------------------

    def _write_game_readme(self, game, gdir):
        lines = [f"# {game.name}", ""]
        lines.append(f"- Template: {game.template.name}")
        if game.game_time:
            from cards.models.game import format_time
            t = format_time(game.game_time)
            if t:
                lines.append(f"- Time: {t}")
        members = game.memberships.select_related("player").all()
        if members:
            lines.append("- Members:")
            for m in members:
                lines.append(f"    - {m.player.name} ({m.role})")
        lines.append("")
        lines.append("## Contents")
        lines.append("")
        lines.append("- `keeper/` — general keeper notes")
        lines.append("- `timeline.md` — the shared timeline")
        lines.append("- `characters/` — characters with their cards")
        lines.append("- `maps/` — hex maps and per-hex notes")
        lines.append("- `situations/` — scenes and encounters")
        (gdir / "README.md").write_text("\n".join(lines) + "\n")

    # -- timeline ----------------------------------------------------------

    def _write_timeline(self, game, gdir):
        timeline = getattr(game, "timeline", None)
        cards = (
            list(TimelineCard.objects.filter(timeline__game=game)
                 .order_by("depth", "position", "pk"))
            if timeline else []
        )
        if not timeline or (not timeline.title and not timeline.notes and not cards):
            return

        by_parent = {}
        for c in cards:
            by_parent.setdefault(c.parent_id, []).append(c)

        lines = [f"# {timeline.title or 'Timeline'}", ""]
        if timeline.notes:
            lines.append(timeline.notes.rstrip())
            lines.append("")

        def render(card, indent):
            pad = "    " * indent
            tint = f" _(tint {card.tint})_" if card.tint else ""
            title = card.title or "(untitled)"
            lines.append(f"{pad}- **{title}**{tint}")
            if card.notes:
                note = card.notes.strip().replace("\n", f"\n{pad}      ")
                lines.append(f"{pad}    - {note}")
            for child in by_parent.get(card.pk, []):
                render(child, indent + 1)

        tops = by_parent.get(None, [])
        if tops:
            lines.append("## Cards")
            lines.append("")
            for card in tops:
                render(card, 0)
            lines.append("")
        (gdir / "timeline.md").write_text("\n".join(lines) + "\n")

    # -- keeper notes ------------------------------------------------------

    def _write_keeper_notes(self, game, gdir):
        notes = list(KeeperNote.objects.filter(game=game).order_by("name"))
        if not notes:
            return
        d = gdir / "keeper"
        d.mkdir(exist_ok=True)
        for note, name in unique_names(notes):
            body = [f"# {note.name}", ""]
            if note.notes:
                body.append(note.notes.rstrip())
                body.append("")
            (d / f"{name}.md").write_text("\n".join(body) + "\n")

    # -- characters --------------------------------------------------------

    def _write_characters(self, game, gdir):
        chars = list(
            Character.objects.filter(game=game)
            .select_related("player", "sheet")
            .order_by("name")
        )
        if not chars:
            return
        d = gdir / "characters"
        d.mkdir(exist_ok=True)
        for char, name in unique_names(chars):
            (d / f"{name}.md").write_text(self._render_character(char))

    def _render_character(self, char):
        lines = [f"# {char.name}", ""]
        if char.callsign:
            lines.append(f"- Callsign: {char.callsign}")
        lines.append(f"- Player: {char.player.name}")
        lines.append(f"- Sheet: {char.sheet.name}")
        lines.append("")
        if char.notes:
            lines.append("## Notes")
            lines.append("")
            lines.append(char.notes.rstrip())
            lines.append("")

        # Tag order from the character's sheet.
        tag_order = list(
            SheetTag.objects.filter(sheet_id=char.sheet_id)
            .order_by("position")
            .values_list("tag__name", flat=True)
        )
        ccards = list(
            CharacterCard.objects.filter(character=char)
            .select_related("card", "tag")
            .order_by("id")
        )
        groups = {}
        for cc in ccards:
            key = cc.tag.name if cc.tag else "Untagged"
            groups.setdefault(key, []).append(cc)

        ordered_keys = [t for t in tag_order if t in groups]
        ordered_keys += [k for k in groups if k not in ordered_keys]

        if ccards:
            lines.append("## Cards")
            lines.append("")
        for key in ordered_keys:
            lines.append(f"### {key}")
            lines.append("")
            for cc in groups[key]:
                cur = effective_level(cc.level, cc.level_mod)
                mod = ""
                if cc.level_mod:
                    mod = f" (baseline {cc.level}, mod {cc.level_mod:+d} → {cur})"
                lines.append(f"- **{cc.card.name}** — level {cur}{mod}")
                lines.append(f"    - Bands: {bands_line(cur)}")
                if cc.card.notes:
                    note = cc.card.notes.strip().replace("\n", "\n      ")
                    lines.append(f"    - {note}")
            lines.append("")
        return "\n".join(lines) + "\n"

    # -- hex maps ----------------------------------------------------------

    def _write_maps(self, game, gdir):
        maps = list(HexMap.objects.filter(game=game).order_by("name"))
        if not maps:
            return
        d = gdir / "maps"
        d.mkdir(exist_ok=True)
        for hexmap, name in unique_names(maps):
            (d / f"{name}.md").write_text(self._render_map(hexmap))

    def _render_map(self, m):
        lines = [f"# {m.name}", ""]
        if m.party_location:
            lines.append(f"- Party location: {m.party_location}")
        if m.party_trail:
            lines.append(f"- Recent trail: {' → '.join(m.party_trail)}")
        lines.append(f"- Hexes placed: {len(m.hexes or {})}")
        lines.append("")

        notes = m.notes or {}
        if notes:
            lines.append("## Hex notes")
            lines.append("")
            for cr in sorted(notes, key=coord_key):
                text = (notes[cr] or "").rstrip()
                if not text:
                    continue
                lines.append(f"### Hex {cr}")
                lines.append("")
                lines.append(text)
                lines.append("")

        site_maps = m.site_maps or {}
        if site_maps:
            lines.append("## Site maps")
            lines.append("")
            for cr in sorted(site_maps, key=coord_key):
                sm = site_maps[cr]
                lines.append(f"### Site at hex {cr}")
                lines.append("")
                nodes = sm.get("nodes", {})
                if nodes:
                    lines.append("Nodes:")
                    for nid, node in nodes.items():
                        label = node.get("label") or node.get("name") or nid
                        lines.append(f"- {label}")
                    lines.append("")
                entrances = sm.get("entrances", [])
                if entrances:
                    lines.append(f"Entrances: {', '.join(str(e) for e in entrances)}")
                    lines.append("")
                routes = sm.get("routes", [])
                if routes:
                    lines.append(f"Routes: {len(routes)}")
                    lines.append("")
        return "\n".join(lines) + "\n"

    # -- situations --------------------------------------------------------

    def _write_situations(self, game, gdir):
        situations = list(
            Situation.objects.filter(game=game)
            .prefetch_related("situation_cards", "cards__card", "cards__character")
            .order_by("id")
        )
        if not situations:
            return
        d = gdir / "situations"
        d.mkdir(exist_ok=True)
        for sit, name in unique_names(situations):
            (d / f"{name}.md").write_text(self._render_situation(sit))

    def _render_situation(self, s):
        lines = [f"# {s.name}", ""]
        lines.append(f"- Type: {s.get_situation_type_display()}")
        lines.append(f"- Resolved: {'yes' if s.resolved else 'no'}")
        if s.location:
            lines.append(f"- Location: {s.location}")
        if s.game_time:
            from cards.models.game import format_time
            t = format_time(s.game_time)
            if t:
                lines.append(f"- Time: {t}")
        lines.append("")

        if s.notes:
            lines.append("## Notes")
            lines.append("")
            lines.append(s.notes.rstrip())
            lines.append("")

        # Live cards + resolved outcomes (assignments map card_id -> die index).
        dice = s.dice or []
        assignments = s.assignments or {}
        live_cards = {str(cc.id): cc for cc in s.cards.all()}
        if live_cards:
            lines.append("## Cards in play")
            lines.append("")
            for cid, cc in live_cards.items():
                cur = effective_level(cc.level, cc.level_mod)
                who = cc.character.name
                line = f"- **{cc.card.name}** ({who}) — level {cur}"
                idx = assignments.get(cid)
                if idx is not None and isinstance(idx, int) and 0 <= idx < len(dice):
                    die = dice[idx]
                    band = get_band_for_die(cur, die) or "?"
                    line += f" — rolled {die} → {band}"
                lines.append(line)
            lines.append("")

        if dice:
            lines.append(f"Dice rolled: {', '.join(str(x) for x in dice)}")
            lines.append("")

        # Archived snapshots (durable record of cards used at roll time).
        snaps = list(s.situation_cards.all())
        if snaps:
            lines.append("## Archived cards")
            lines.append("")
            for sc in snaps:
                cur = effective_level(sc.level, sc.level_mod)
                used = "used" if sc.used else "not used"
                who = f" ({sc.character_name})" if sc.character_name else ""
                lines.append(f"- **{sc.name}**{who} — level {cur}, {used}")
                if sc.notes:
                    note = sc.notes.strip().replace("\n", "\n      ")
                    lines.append(f"    - {note}")
            lines.append("")
        return "\n".join(lines) + "\n"
