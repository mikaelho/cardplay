"""Cardplay-specific hooks for the Alive framework."""

import random
from asgiref.sync import sync_to_async
from django.apps import apps

from alive.store import get_store, acquire_lock, release_lock, get_lock_holder
from alive.components.editable_field import render_markdown_safe
from cards.ui import snippet as _snippet


# --- Helper ---

async def _broadcast(socket, model_class):
    """Broadcast state change for a model."""
    store = get_store(model_class)
    await socket.broadcast(store.channel, {"action": "state_changed"})


async def _refresh(socket):
    """Trigger the framework's built-in view refresh."""
    await socket.liveview._refresh_view_async(socket)


# --- Data Loaders (moved from views.py private methods) ---

async def load_situation_data(socket, is_situation_page, is_map_page):
    """Load situation-specific context when viewing Situation or Map pages."""
    if not is_situation_page and not is_map_page:
        return

    game_id = socket.context.frame.get("game_id")
    if not game_id:
        return

    @sync_to_async(thread_sensitive=False)
    def _fetch():
        Situation = apps.get_model('cards', 'Situation')

        if is_map_page:
            # Map page: only show unresolved situations (not notes)
            active = Situation.objects.filter(
                game_id=game_id, resolved=False, situation_type="situation"
            ).order_by('-pk').first()
            past = []
            if not active:
                return None, [], [], [], {}, False, False
        else:
            # Situation page: show most recent regardless of status
            situations = list(
                Situation.objects.filter(game_id=game_id).order_by('-pk')
            )
            if not situations:
                return None, [], [], [], {}, False, False
            active = situations[0]
            past = [{"id": str(s.pk), "name": s.name} for s in situations[1:]]
        dice = active.dice or []
        assignments = active.assignments or {}

        # Compute which die indices are already assigned
        assigned_indices = set(assignments.values())

        # Load cards in the active situation
        from cards.models.card import get_bands_for_level, get_band_for_die
        cards = []
        if dice:
            # Post-roll: read from SituationCard snapshots
            for sc in active.situation_cards.all():
                card_id = str(sc.pk)
                assigned_die_index = assignments.get(card_id)
                assigned_die_value = None
                assigned_band_label = None
                if assigned_die_index is not None and assigned_die_index < len(dice):
                    assigned_die_value = dice[assigned_die_index]
                    assigned_band_label = get_band_for_die(sc.level, assigned_die_value)

                card_bands = get_bands_for_level(sc.level)
                for band in card_bands:
                    band["highlighted"] = (band["label"] == assigned_band_label) if assigned_band_label else False

                available_dice = []
                for idx, val in enumerate(dice):
                    if idx not in assigned_indices:
                        available_dice.append({"index": idx, "value": val})

                cards.append({
                    "id": card_id,
                    "name": sc.name,
                    "notes": sc.notes,
                    "character_name": sc.character_name,
                    "level": sc.level,
                    "bands": card_bands,
                    "assigned_die_value": assigned_die_value,
                    "assigned_die_index": assigned_die_index,
                    "assigned_band": assigned_band_label or "",
                    "available_dice": available_dice,
                    "used": sc.used,
                })
        else:
            # Pre-roll: read from CharacterCard M2M
            for cc in active.cards.select_related('card', 'character').all():
                cards.append({
                    "id": str(cc.pk),
                    "name": cc.card.name,
                    "notes": cc.card.notes or "",
                    "character_name": cc.character.name if cc.character else "",
                    "level": cc.level,
                    "bands": get_bands_for_level(cc.level),
                    "assigned_die_value": None,
                    "assigned_die_index": None,
                    "available_dice": [],
                })

        return active, cards, past, dice, assignments, active.dice_assigned, active.resolved

    active, cards, past, dice, assignments, dice_assigned, resolved = await _fetch()

    if active is None:
        socket.context.hand_active_situation_id = None
        socket.context.active_situation_name = ""
        socket.context.active_situation_notes = ""
        socket.context.situation_cards = []
        socket.context.past_situations = []
        socket.context.situation_dice = []
        socket.context.situation_assignments = {}
        socket.context.situation_dice_assigned = False
        socket.context.situation_resolved = False
        socket.context.situation_all_assigned = False
        if is_map_page:
            socket.context.map_situation_active = False
        return

    # Build enriched dice list for display with SVGs
    from cards.ui import render_die_svg, DIE_CSS
    assigned_indices = set(assignments.values()) if assignments else set()
    # Reverse mapping: die index -> card_id
    index_to_card = {v: k for k, v in assignments.items()} if assignments else {}
    dice_display = [
        {"index": i, "value": v, "assigned": i in assigned_indices,
         "card_id": index_to_card.get(i, ""),
         "svg": render_die_svg(v, css_class="h-8 w-8")}
        for i, v in enumerate(dice)
    ] if dice else []

    # Add SVGs to card data
    dashed_svg = render_die_svg(0, css_class="h-8 w-8", dashed=True)
    for card in cards:
        if card["assigned_die_value"] is not None:
            card["assigned_die_svg"] = render_die_svg(card["assigned_die_value"], css_class="h-8 w-8")
        card["placeholder_svg"] = dashed_svg
        # Add SVGs to available dice
        for die in card.get("available_dice", []):
            die["svg"] = render_die_svg(die["value"], css_class="h-8 w-8")

    # Annotate cards with editing state for keeper
    edit_id = socket.context.situation_card_editing_id
    edit_field = socket.context.situation_card_editing_field
    edit_value = socket.context.situation_card_editing_value
    for card in cards:
        card["editing_name"] = (card["id"] == edit_id and edit_field == "name")
        card["editing_notes"] = (card["id"] == edit_id and edit_field == "notes")
        card["editing_value"] = edit_value if card["id"] == edit_id else ""

    socket.context.hand_active_situation_id = active.pk
    socket.context.active_situation_name = active.name
    socket.context.active_situation_notes = active.notes or ""
    socket.context.situation_cards = cards
    socket.context.past_situations = past
    socket.context.situation_dice = dice_display
    socket.context.situation_assignments = assignments
    socket.context.situation_dice_assigned = dice_assigned
    socket.context.situation_resolved = resolved
    socket.context.situation_all_assigned = bool(dice and cards and len(assignments) >= len(cards))

    if is_map_page:
        socket.context.map_situation_active = not resolved

    # Load keeper's available cards for the picker
    if socket.context.is_keeper and not dice:
        keeper_char_id = socket.context.keeper_character_id

        @sync_to_async(thread_sensitive=False)
        def _fetch_keeper_cards():
            CharacterCard = apps.get_model('cards', 'CharacterCard')
            Character = apps.get_model('cards', 'Character')
            GameMembership = apps.get_model('cards', 'GameMembership')
            situation_card_pks = set(
                active.cards.values_list('pk', flat=True)
            ) if active else set()
            # Keeper's own cards
            keeper_cards = []
            if keeper_char_id:
                keeper_cards = [
                    {"id": str(cc.pk), "name": cc.card.name, "level": cc.level}
                    for cc in CharacterCard.objects.filter(
                        character_id=keeper_char_id
                    ).select_related('card')
                    if cc.pk not in situation_card_pks
                ]
            # Fetch player character cards grouped by character
            player_groups = []
            player_member_ids = GameMembership.objects.filter(
                game_id=active.game_id, role="player"
            ).values_list('player_id', flat=True)
            player_chars = Character.objects.filter(
                game_id=active.game_id, player_id__in=player_member_ids
            ).order_by('name')
            for char in player_chars:
                char_cards = [
                    {"id": str(cc.pk), "name": cc.card.name, "level": cc.level}
                    for cc in CharacterCard.objects.filter(
                        character_id=char.pk
                    ).select_related('card')
                    if cc.pk not in situation_card_pks
                ]
                if char_cards:
                    player_groups.append({
                        "character_name": char.name,
                        "cards": char_cards,
                    })
            return keeper_cards, player_groups

        keeper_cards, player_groups = await _fetch_keeper_cards()
        socket.context.keeper_available_cards = keeper_cards
        socket.context.keeper_player_card_groups = player_groups


async def _commit_river(socket):
    """Save the current in-progress river to the database."""
    current = socket.context.hex_current_river
    map_id = socket.context.hex_map_id
    if not current or len(current) < 2 or not map_id:
        socket.context.hex_current_river = []
        return

    river_to_save = list(current)
    HexMap = apps.get_model('cards', 'HexMap')

    @sync_to_async(thread_sensitive=False)
    def _save():
        hex_map = HexMap.objects.get(pk=map_id)
        rivers = hex_map.rivers or []
        rivers.append(river_to_save)
        hex_map.rivers = rivers
        hex_map.save(update_fields=["rivers"])

    await _save()
    socket.context.hex_current_river = []
    await _broadcast(socket, HexMap)


async def _close_map_detail(socket):
    """Close map detail popup, releasing any locks."""
    detail_id = (socket.context.map_detail or {}).get("id", "")
    field_name = socket.context.map_detail_editing
    if detail_id and field_name:
        release_lock("cards.situation", detail_id, field_name,
                     socket.context.session_id)
    socket.context.map_detail = {}
    socket.context.map_detail_editing = ""
    socket.context.map_detail_draft = ""


async def _refresh_map_detail(socket):
    """Refresh detail popup data from DB."""
    detail_id = (socket.context.map_detail or {}).get("id", "")
    if not detail_id:
        return

    @sync_to_async(thread_sensitive=False)
    def _fetch_detail():
        Situation = apps.get_model('cards', 'Situation')
        try:
            s = Situation.objects.get(pk=detail_id)
            data = {
                "id": str(s.pk),
                "name": s.name,
                "notes": s.notes,
                "type": s.situation_type,
                "type_label": s.get_situation_type_display(),
                "location": s.location,
            }
            # Include condensed cards for resolved situations
            if s.resolved and s.dice:
                from cards.models.card import get_band_for_die
                assignments = s.assignments or {}
                dice = s.dice
                detail_cards = []
                for sc in s.situation_cards.all():
                    card_id = str(sc.pk)
                    assigned_die_index = assignments.get(card_id)
                    band = ""
                    if assigned_die_index is not None and assigned_die_index < len(dice):
                        band = get_band_for_die(sc.level, dice[assigned_die_index]) or ""
                    detail_cards.append({
                        "name": sc.name,
                        "notes": sc.notes,
                        "band": band,
                    })
                data["cards"] = detail_cards
            return data
        except Situation.DoesNotExist:
            return None

    data = await _fetch_detail()
    if not data:
        socket.context.map_detail = {}
        socket.context.map_detail_editing = ""
        socket.context.map_detail_draft = ""
        return

    sid = socket.context.session_id
    data["name_locked"] = (
        get_lock_holder("cards.situation", data["id"], "name") not in (None, sid)
    )
    data["notes_locked"] = (
        get_lock_holder("cards.situation", data["id"], "notes") not in (None, sid)
    )
    data["notes_html"] = (
        render_markdown_safe(data["notes"]) if data["notes"] else ""
    )
    socket.context.map_detail = data


async def load_map_data(socket):
    """Load map-specific context when viewing the HexMap model."""
    from cards.ui import render_hex_map, render_hex_palette, render_overlay_palette, get_adjacent_hexes

    HexMap = apps.get_model('cards', 'HexMap')
    edit_mode = socket.context.hex_map_edit and socket.context.is_keeper
    show_overlays = socket.context.hex_show_overlays and socket.context.is_keeper

    # Get the HexMap instance from the game context
    game_id = socket.context.frame.get("game_id")

    @sync_to_async(thread_sensitive=False)
    def _fetch_map():
        qs = HexMap.objects.all()
        if game_id:
            qs = qs.filter(game_id=game_id)
        hex_map = qs.first()
        if not hex_map and game_id:
            hex_map = HexMap.objects.create(name="Map", game_id=game_id)
        if hex_map:
            return hex_map.pk, hex_map.hexes or {}, hex_map.rivers or [], hex_map.overlays or {}, hex_map.barriers or {}, hex_map.party_location or "", hex_map.party_trail or [], hex_map.notes or {}, hex_map.site_maps or {}, hex_map.revealed_overlays or {}
        return None, {}, [], {}, {}, "", [], {}, {}, {}

    map_id, hexes, rivers, overlays, barriers, party_loc, party_trail, notes, site_maps, revealed_overlays = await _fetch_map()

    # Fetch timeline data (situations/notes for this game)
    timeline_entries = []
    timeline_locs = None
    if game_id:
        @sync_to_async(thread_sensitive=False)
        def _fetch_timeline():
            Situation = apps.get_model('cards', 'Situation')
            Game = apps.get_model('cards', 'Game')
            entries = list(
                Situation.objects.filter(game_id=game_id)
                .exclude(name="")
                .order_by('-pk')
                .values('pk', 'name', 'situation_type', 'location', 'notes', 'game_time')
            )
            game = Game.objects.get(pk=game_id)
            return entries, game.game_time or {}

        raw_entries, current_game_time = await _fetch_timeline()

        from cards.models.game import format_time, time_group_key
        socket.context.current_game_time = format_time(current_game_time)

        # Build template-ready entries with time separators
        prev_group = None
        for i, e in enumerate(raw_entries):
            is_last = i == len(raw_entries) - 1
            gt = e.get('game_time') or {}
            group = time_group_key(gt)
            shift_label = gt.get("shift", "").title() if gt else ""
            entry = {
                "id": str(e['pk']),
                "name": e['name'],
                "situation_type": e['situation_type'],
                "location": e['location'],
                "is_first": i == 0,
                "is_last": is_last,
                "is_current": is_last,
                "time_separator": group if group and group != prev_group else "",
                "shift": shift_label,
            }
            if group:
                prev_group = group
            timeline_entries.append(entry)

        # Build location list for SVG hover highlights (chronological order)
        timeline_locs = [
            (str(e['pk']), e['location'])
            for e in reversed(raw_entries)
        ]

    socket.context.timeline_entries = timeline_entries
    socket.context.party_location = party_loc

    # Compute adjacent hexes for movement (keeper, non-edit mode)
    adjacent = None
    if socket.context.is_keeper and not edit_mode:
        if party_loc:
            pc, pr = map(int, party_loc.split(","))
            adjacent = get_adjacent_hexes(pc, pr)
        else:
            # No party yet: all hexes are valid for initial placement
            adjacent = {f"{c},{r}" for c in range(12) for r in range(12)}

    # Include the in-progress river for preview
    all_rivers = list(rivers)
    if socket.context.hex_current_river and len(socket.context.hex_current_river) >= 2:
        all_rivers.append(socket.context.hex_current_river)

    socket.context.hex_map_id = map_id
    socket.context.hex_map_svg = render_hex_map(
        hexes=hexes, rivers=all_rivers, overlays=overlays,
        barriers=barriers, edit_mode=edit_mode,
        is_keeper=socket.context.is_keeper,
        show_overlays=show_overlays,
        party_location=party_loc, party_trail=party_trail,
        adjacent_hexes=adjacent,
        timeline_locations=timeline_locs if game_id else None,
        notes=notes,
        site_maps=site_maps,
        revealed_overlays=revealed_overlays,
    )
    if edit_mode:
        socket.context.hex_map_palette = render_hex_palette(
            active_symbol=socket.context.hex_active_symbol,
        )
        socket.context.hex_overlay_palette = render_overlay_palette(
            active_overlay=socket.context.hex_active_overlay,
        )

    # Refresh site map SVG if modal is open
    if socket.context.site_map_open and socket.context.site_map_hex:
        from cards.ui import render_site_map_svg
        socket.context.site_map_svg = render_site_map_svg(
            site_data=socket.context.site_map_data,
            edit_mode=socket.context.site_map_edit,
            active_tool=socket.context.site_map_tool,
            route_from=socket.context.site_map_route_from,
            selected_type=socket.context.site_map_selected_type,
            selected_id=socket.context.site_map_selected_id,
        )

    # Refresh detail popup if open
    if socket.context.map_detail:
        await _refresh_map_detail(socket)


async def _save_site_map_data(socket):
    """Persist site_map_data to DB for the current hex."""
    map_id = socket.context.hex_map_id
    hex_key = socket.context.site_map_hex
    if not map_id or not hex_key:
        return
    site_data = socket.context.site_map_data
    HexMap = apps.get_model('cards', 'HexMap')

    @sync_to_async(thread_sensitive=False)
    def _save():
        hex_map = HexMap.objects.get(pk=map_id)
        site_maps = hex_map.site_maps or {}
        # Only store if there's actual content
        has_content = (
            site_data.get("nodes")
            or site_data.get("routes")
            or site_data.get("entrances")
        )
        if has_content:
            site_maps[hex_key] = site_data
        else:
            site_maps.pop(hex_key, None)
        hex_map.site_maps = site_maps
        hex_map.save(update_fields=["site_maps"])

    await _save()


async def _handle_site_map_edit_click(socket, click_type, click_id):
    """Handle clicks in site map edit mode."""
    from cards.ui import _sm_is_valid_route, _sm_route_key
    tool = socket.context.site_map_tool
    data = socket.context.site_map_data

    if not data.get("nodes"):
        data["nodes"] = {}
    if not data.get("routes"):
        data["routes"] = []
    if not data.get("entrances"):
        data["entrances"] = []

    # Direct click on existing route -- cycle types (no deletion)
    if click_type == "route" and tool != "erase_route":
        for r in data["routes"]:
            if _sm_route_key(r["from"], r["to"]) == click_id:
                if r["type"] == "open":
                    r["type"] = "closed"
                elif r["type"] == "closed":
                    r["type"] = "hidden"
                else:
                    r["type"] = "open"
                await _save_site_map_data(socket)
                break
        socket.context.site_map_route_from = -1
        return

    # Direct click on existing entrance -- cycle types (no deletion)
    if click_type == "entrance" and tool != "erase_entrance":
        eidx = int(click_id)
        for e in data["entrances"]:
            if e["node"] == eidx:
                if e["type"] == "visible":
                    e["type"] = "hidden"
                else:
                    e["type"] = "visible"
                await _save_site_map_data(socket)
                break
        return

    # Node placement tools
    if tool in ("feature", "danger", "treasure"):
        if click_type in ("node", "empty_node"):
            idx = click_id
            data["nodes"][idx] = {
                "type": tool,
                "name": "",
                "notes": "",
            }
            await _save_site_map_data(socket)
        return

    # Route tool: 2-click creation
    if tool == "route":
        if click_type in ("node", "empty_node"):
            idx = int(click_id)
            if socket.context.site_map_route_from < 0:
                socket.context.site_map_route_from = idx
            else:
                first = socket.context.site_map_route_from
                socket.context.site_map_route_from = -1
                if first != idx and _sm_is_valid_route(first, idx):
                    rkey = _sm_route_key(first, idx)
                    existing = [
                        r for r in data["routes"]
                        if _sm_route_key(r["from"], r["to"]) == rkey
                    ]
                    if existing:
                        r = existing[0]
                        if r["type"] == "open":
                            r["type"] = "closed"
                        elif r["type"] == "closed":
                            r["type"] = "hidden"
                        else:
                            r["type"] = "open"
                    else:
                        data["routes"].append({
                            "from": min(first, idx),
                            "to": max(first, idx),
                            "type": "open",
                            "name": "",
                            "notes": "",
                        })
                    await _save_site_map_data(socket)
        return

    # Entrance tool: click on outer node to add/cycle
    if tool == "entrance":
        if click_type in ("node", "empty_node"):
            idx = int(click_id)
            if 1 <= idx <= 6:
                existing = [e for e in data["entrances"] if e["node"] == idx]
                if existing:
                    e = existing[0]
                    if e["type"] == "visible":
                        e["type"] = "hidden"
                    else:
                        e["type"] = "visible"
                else:
                    data["entrances"].append({
                        "node": idx,
                        "type": "visible",
                        "name": "",
                        "notes": "",
                    })
                await _save_site_map_data(socket)
        return

    # Erase tools
    if tool == "erase_node":
        if click_type == "node":
            data["nodes"].pop(click_id, None)
            # Also remove routes and entrances connected to this node
            idx = int(click_id)
            data["routes"] = [
                r for r in data["routes"]
                if r["from"] != idx and r["to"] != idx
            ]
            data["entrances"] = [
                e for e in data["entrances"] if e["node"] != idx
            ]
            await _save_site_map_data(socket)
        return

    if tool == "erase_route":
        if click_type == "route":
            from cards.ui import _sm_route_key as _rk
            data["routes"] = [
                r for r in data["routes"]
                if _rk(r["from"], r["to"]) != click_id
            ]
            await _save_site_map_data(socket)
        return

    if tool == "erase_entrance":
        if click_type == "entrance":
            idx = int(click_id)
            data["entrances"] = [
                e for e in data["entrances"] if e["node"] != idx
            ]
            await _save_site_map_data(socket)
        return


async def _handle_site_map_view_click(socket, click_type, click_id):
    """Handle clicks in site map view mode -- select element for detail."""
    from cards.ui import _sm_route_key
    data = socket.context.site_map_data

    socket.context.site_map_detail_editing = ""
    socket.context.site_map_detail_draft = ""

    if click_type == "node" and click_id in data.get("nodes", {}):
        node = data["nodes"][click_id]
        socket.context.site_map_selected_type = "node"
        socket.context.site_map_selected_id = click_id
        socket.context.site_map_detail_name = node.get("name", "")
        socket.context.site_map_detail_notes = node.get("notes", "")
    elif click_type == "route":
        for r in data.get("routes", []):
            if _sm_route_key(r["from"], r["to"]) == click_id:
                socket.context.site_map_selected_type = "route"
                socket.context.site_map_selected_id = click_id
                socket.context.site_map_detail_name = r.get("name", "")
                socket.context.site_map_detail_notes = r.get("notes", "")
                break
    elif click_type == "entrance":
        for e in data.get("entrances", []):
            if str(e["node"]) == click_id:
                socket.context.site_map_selected_type = "entrance"
                socket.context.site_map_selected_id = click_id
                socket.context.site_map_detail_name = e.get("name", "")
                socket.context.site_map_detail_notes = e.get("notes", "")
                break
    else:
        # Deselect
        socket.context.site_map_selected_type = ""
        socket.context.site_map_selected_id = ""
        socket.context.site_map_detail_name = ""
        socket.context.site_map_detail_notes = ""


async def load_hand_data(socket):
    """Load hand data for the player's character."""
    character_id = socket.context.hand_character_id
    if not character_id:
        return

    game_id = socket.context.frame.get("game_id")

    @sync_to_async(thread_sensitive=False)
    def _fetch():
        CharacterCard = apps.get_model('cards', 'CharacterCard')
        Hand = apps.get_model('cards', 'Hand')
        Situation = apps.get_model('cards', 'Situation')

        non_attr_count = CharacterCard.objects.filter(
            character_id=character_id
        ).exclude(tag__name="Attribute").count()

        hand = Hand.objects.filter(character_id=character_id).order_by('-id').first()
        hand_cards = []
        hand_drawn = False
        if hand:
            hand_drawn = True
            for cc in hand.cards.select_related('card', 'tag').all():
                from cards.models.card import get_bands_for_level
                hand_cards.append({
                    "id": str(cc.pk),
                    "name": cc.card.name,
                    "notes": cc.card.notes or "",
                    "level": cc.level,
                    "bands": get_bands_for_level(cc.level),
                    "is_attribute": cc.tag_id is not None and cc.tag.name == "Attribute",
                })

            # Add attribute cards not already in the hand (always shown)
            hand_pks = set(hand.cards.values_list('pk', flat=True))
        else:
            hand_pks = set()

        # Always add attribute cards (shown regardless of draw state)
        for cc in CharacterCard.objects.filter(
            character_id=character_id, tag__name="Attribute"
        ).select_related('card', 'tag').exclude(pk__in=hand_pks):
            from cards.models.card import get_bands_for_level
            hand_cards.append({
                "id": str(cc.pk),
                "name": cc.card.name,
                "notes": cc.card.notes or "",
                "level": cc.level,
                "bands": get_bands_for_level(cc.level),
                "is_attribute": True,
            })

        # Sort: attribute cards first, then normal cards
        hand_cards.sort(key=lambda c: (not c["is_attribute"], c["name"]))

        # Mark first non-attribute card for visual separator
        has_attr = any(c["is_attribute"] for c in hand_cards)
        if has_attr:
            for c in hand_cards:
                if not c["is_attribute"]:
                    c["separator_before"] = True
                    break

        # Look up active situation (latest by pk for this game)
        active_sit = None
        situation_card_pks = set()
        if game_id:
            active_sit = Situation.objects.filter(game_id=game_id).order_by('-pk').first()
            if active_sit:
                situation_card_pks = set(
                    active_sit.cards.values_list('pk', flat=True)
                )

        # Mark cards that are in the active situation
        for card in hand_cards:
            card["in_situation"] = int(card["id"]) in situation_card_pks

        sit_dice = active_sit.dice if active_sit else []

        # Determine if player can draw more cards
        # No drawing during an active situation or when draw_active is False
        drawn_non_attr = sum(1 for c in hand_cards if not c["is_attribute"])
        has_active_situation = game_id and Situation.objects.filter(
            game_id=game_id, situation_type="situation", resolved=False
        ).exists()
        draw_active = not hand or hand.draw_active
        hand_can_draw = (
            not has_active_situation
            and draw_active
            and drawn_non_attr < non_attr_count
        )

        return non_attr_count, hand_cards, hand_drawn, hand_can_draw, active_sit, sit_dice

    non_attr_count, hand_cards, hand_drawn, hand_can_draw, active_sit, sit_dice = await _fetch()

    socket.context.hand_card_count = non_attr_count
    socket.context.hand_drawn = hand_drawn
    socket.context.hand_cards = hand_cards
    socket.context.hand_can_draw = hand_can_draw
    socket.context.hand_active_situation_id = active_sit.pk if active_sit else None
    # Only set situation_dice if not already set by load_situation_data (which has richer data)
    if not socket.context.situation_dice:
        socket.context.situation_dice = sit_dice


# --- Event Handler ---

async def cardplay_event_handler(event, payload, socket):
    """Handle all cardplay-specific events. Returns True if handled."""
    HexMap = apps.get_model('cards', 'HexMap')

    # --- Keeper-specific cancel_create ---
    if event == "cancel_create":
        if socket.context.keeper_creating:
            socket.context.keeper_creating = False
            socket.context.keeper_adding = False
            socket.context.creating = False
            socket.context.create_values = {}
            socket.context.create_error = ""
            return True
        return False

    # --- Keeper-specific save_create ---
    if event == "save_create":
        if socket.context.keeper_creating:
            # Keeper card creation: validate against Card fields, create Card + CharacterCard + add to situation
            missing = []
            for f in socket.context.create_fields:
                if f["required"] and not socket.context.create_values.get(f["name"]):
                    missing.append(f["label"])
            if missing:
                socket.context.create_error = f"Required: {', '.join(missing)}"
                return True

            Card = apps.get_model('cards', 'Card')
            card_store = get_store(Card)
            card = await card_store.create_item(socket.context.create_values)
            if not card:
                socket.context.create_error = "Failed to create card"
                return True

            situation_id = socket.context.hand_active_situation_id
            keeper_char_id = socket.context.keeper_character_id
            if situation_id:
                @sync_to_async(thread_sensitive=False)
                def _link_card():
                    CharacterCard = apps.get_model('cards', 'CharacterCard')
                    Situation = apps.get_model('cards', 'Situation')
                    Character = apps.get_model('cards', 'Character')
                    sit = Situation.objects.get(pk=situation_id)
                    if sit.dice:
                        return None
                    # Auto-create keeper character if needed
                    char_id = keeper_char_id
                    if not char_id:
                        player_id = socket.context.player_id
                        if not player_id or not isinstance(player_id, int):
                            return None
                        game = sit.game
                        sheet = game.template.sheets.first()
                        if not sheet:
                            return None
                        char, _created = Character.objects.get_or_create(
                            player_id=player_id,
                            game=game,
                            defaults={"name": "Keeper", "sheet": sheet},
                        )
                        char_id = char.pk
                    cc = CharacterCard.objects.create(
                        character_id=char_id,
                        card=card,
                        level=4,
                    )
                    sit.cards.add(cc)
                    return char_id

                result_char_id = await _link_card()
                if result_char_id and not keeper_char_id:
                    socket.context.keeper_character_id = result_char_id

            socket.context.creating = False
            socket.context.keeper_creating = False
            socket.context.keeper_adding = False
            socket.context.create_values = {}
            socket.context.create_error = ""
            await _refresh(socket)
            await _broadcast(socket, HexMap)
            return True
        return False

    # --- sync_sheet_cards ---
    if event == "sync_sheet_cards":
        item_id = payload.get("item_id", "")
        if item_id:
            Character = apps.get_model('cards', 'Character')
            has_sheet_defaults = hasattr(Character, 'sheet') and hasattr(Character.sheet, 'field')
            if has_sheet_defaults:
                @sync_to_async(thread_sensitive=False)
                def _sync():
                    character = Character.objects.get(pk=int(item_id))
                    if not character.sheet_id:
                        return
                    SheetDefaultCard = apps.get_model('cards', 'SheetDefaultCard')
                    CardModel = apps.get_model('cards', 'Card')
                    CharacterCard = apps.get_model('cards', 'CharacterCard')
                    existing = set(
                        CharacterCard.objects.filter(character=character)
                        .values_list('card__name', 'tag_id')
                    )
                    for dc in SheetDefaultCard.objects.filter(sheet_id=character.sheet_id):
                        if (dc.name, dc.tag_id) not in existing:
                            card = CardModel.objects.create(name=dc.name, notes=dc.notes)
                            CharacterCard.objects.create(
                                character=character, card=card, level=4, tag=dc.tag,
                            )

                await _sync()
                await _refresh(socket)
                await _broadcast(socket, HexMap)
        return True

    # --- Hand events ---

    if event == "toggle_hand_collapsed":
        socket.context.hand_collapsed = not socket.context.hand_collapsed
        return True

    if event == "draw_hand":
        character_id = socket.context.hand_character_id
        if character_id:
            @sync_to_async(thread_sensitive=False)
            def _draw_one():
                CharacterCard = apps.get_model('cards', 'CharacterCard')
                Hand = apps.get_model('cards', 'Hand')

                hand, _created = Hand.objects.get_or_create(
                    character_id=character_id, defaults={"name": "Hand"}
                )
                existing_pks = set(hand.cards.values_list('pk', flat=True))
                available = list(CharacterCard.objects.filter(
                    character_id=character_id
                ).exclude(tag__name="Attribute").exclude(pk__in=existing_pks))
                if available:
                    card = random.choice(available)
                    hand.cards.add(card)

            await _draw_one()
            await load_hand_data(socket)
        return True

    if event == "toggle_hand_situation":
        card_id = payload.get("card_id", "")
        situation_id = socket.context.hand_active_situation_id
        if card_id and situation_id and socket.context.hand_is_player and not socket.context.situation_dice:
            @sync_to_async(thread_sensitive=False)
            def _toggle():
                Situation = apps.get_model('cards', 'Situation')
                CharacterCard = apps.get_model('cards', 'CharacterCard')
                sit = Situation.objects.get(pk=situation_id)
                if sit.dice:
                    return  # Frozen after roll
                cc = CharacterCard.objects.select_related('tag').get(pk=int(card_id))
                is_attr = cc.tag_id is not None and cc.tag.name == "Attribute"
                if is_attr:
                    # Attribute card: only one at a time per character
                    attr_in_sit = sit.cards.filter(
                        character_id=cc.character_id, tag__name="Attribute"
                    )
                    if attr_in_sit.filter(pk=cc.pk).exists():
                        # Clicked the already-selected attribute -> remove it
                        sit.cards.remove(cc.pk)
                    else:
                        # Swap: remove old attribute(s), add this one
                        for old in attr_in_sit:
                            sit.cards.remove(old.pk)
                        sit.cards.add(cc.pk)
                else:
                    # Normal toggle
                    if sit.cards.filter(pk=cc.pk).exists():
                        sit.cards.remove(cc.pk)
                    else:
                        sit.cards.add(cc.pk)

            await _toggle()
            await load_hand_data(socket)
            await _broadcast(socket, HexMap)
        return True

    # --- Situation card events ---

    if event == "remove_situation_card":
        card_id = payload.get("card_id", "")
        situation_id = payload.get("situation_id", "")
        if card_id and situation_id and not socket.context.situation_dice:
            @sync_to_async(thread_sensitive=False)
            def _remove():
                Situation = apps.get_model('cards', 'Situation')
                sit = Situation.objects.get(pk=int(situation_id))
                if sit.dice:
                    return  # Frozen after roll
                sit.cards.remove(int(card_id))

            await _remove()
            await _refresh(socket)
            if socket.context.hand_is_player:
                await load_hand_data(socket)
            await _broadcast(socket, HexMap)
        return True

    if event == "adjust_situation_card_level":
        card_id = payload.get("card_id", "")
        delta = int(payload.get("delta", 0))
        if card_id and delta and socket.context.is_keeper:
            has_dice = bool(socket.context.situation_dice)

            @sync_to_async(thread_sensitive=False)
            def _adjust():
                if has_dice:
                    SituationCard = apps.get_model('cards', 'SituationCard')
                    sc = SituationCard.objects.get(pk=int(card_id))
                    sc.level = max(1, min(10, sc.level + delta))
                    sc.save(update_fields=["level"])
                else:
                    CharacterCard = apps.get_model('cards', 'CharacterCard')
                    cc = CharacterCard.objects.get(pk=int(card_id))
                    cc.level = max(1, min(10, cc.level + delta))
                    cc.save(update_fields=["level"])

            await _adjust()
            await _refresh(socket)
            await _broadcast(socket, HexMap)
        return True

    if event == "start_situation_card_edit":
        card_id = payload.get("card_id", "")
        field = payload.get("field", "")
        if card_id and field in ("name", "notes") and socket.context.is_keeper:
            socket.context.situation_card_editing_id = card_id
            socket.context.situation_card_editing_field = field
        return True

    if event == "cancel_situation_card_edit":
        socket.context.situation_card_editing_id = ""
        socket.context.situation_card_editing_field = ""
        socket.context.situation_card_editing_value = ""
        return True

    if event == "save_situation_card_edit":
        card_id = payload.get("card_id", "")
        field = payload.get("field", "")
        value = payload.get("value", "")
        if isinstance(value, list):
            value = value[0] if value else ""
        if card_id and field in ("name", "notes") and socket.context.is_keeper:
            has_dice = bool(socket.context.situation_dice)
            value = value.strip()

            @sync_to_async(thread_sensitive=False)
            def _save():
                if has_dice:
                    SituationCard = apps.get_model('cards', 'SituationCard')
                    sc = SituationCard.objects.get(pk=int(card_id))
                    setattr(sc, field, value)
                    sc.save(update_fields=[field])
                else:
                    CharacterCard = apps.get_model('cards', 'CharacterCard')
                    cc = CharacterCard.objects.select_related('card').get(pk=int(card_id))
                    setattr(cc.card, field, value)
                    cc.card.save(update_fields=[field])

            await _save()
            socket.context.situation_card_editing_id = ""
            socket.context.situation_card_editing_field = ""
            socket.context.situation_card_editing_value = ""
            await _refresh(socket)
            await _broadcast(socket, HexMap)
        else:
            socket.context.situation_card_editing_id = ""
            socket.context.situation_card_editing_field = ""
            socket.context.situation_card_editing_value = ""
        return True

    if event == "rename_situation":
        new_name = payload.get("value", "").strip()
        situation_id = socket.context.hand_active_situation_id
        if new_name and situation_id:
            @sync_to_async(thread_sensitive=False)
            def _rename():
                Situation = apps.get_model('cards', 'Situation')
                Situation.objects.filter(pk=situation_id).update(name=new_name)

            await _rename()
            await _refresh(socket)
            await _broadcast(socket, HexMap)
        return True

    # --- Keeper add/create events ---

    if event == "keeper_start_add":
        socket.context.keeper_adding = True
        socket.context.keeper_creating = False
        return True

    if event == "keeper_cancel_add":
        socket.context.keeper_adding = False
        if socket.context.keeper_creating:
            socket.context.keeper_creating = False
            socket.context.creating = False
            socket.context.create_values = {}
            socket.context.create_error = ""
        return True

    if event == "keeper_start_create":
        Card = apps.get_model('cards', 'Card')
        card_create_fields = Card.get_creatable_fields()
        fields_with_choices = []
        for i, f in enumerate(card_create_fields):
            fields_with_choices.append({**f, "value": "", "autofocus": i == 0})
        socket.context.create_fields = fields_with_choices
        socket.context.create_values = {}
        socket.context.create_error = ""
        socket.context.create_title = Card._meta.verbose_name.title()
        socket.context.creating = True
        socket.context.keeper_creating = True
        return True

    if event == "keeper_add_card":
        card_id = payload.get("card_id", "")
        situation_id = socket.context.hand_active_situation_id
        if card_id and situation_id and socket.context.is_keeper:
            @sync_to_async(thread_sensitive=False)
            def _add():
                Situation = apps.get_model('cards', 'Situation')
                sit = Situation.objects.get(pk=situation_id)
                if sit.dice:
                    return
                sit.cards.add(int(card_id))

            await _add()
            socket.context.keeper_adding = False
            await _refresh(socket)
            await _broadcast(socket, HexMap)
        return True

    # --- Map editing events ---

    if event == "toggle_map_edit":
        if socket.context.is_keeper:
            # Commit any in-progress river before leaving edit mode
            if socket.context.hex_map_edit and socket.context.hex_current_river:
                await _commit_river(socket)
            socket.context.hex_map_edit = not socket.context.hex_map_edit
            socket.context.hex_active_symbol = ""
            socket.context.hex_active_overlay = ""
            socket.context.hex_overlay_mode = False
            socket.context.hex_river_drawing = False
            socket.context.hex_current_river = []
            socket.context.hex_action_hex = ""
            socket.context.hex_action_is_adjacent = False
            socket.context.hex_selected_hex = ""
            socket.context.hex_note_editing = False
            await load_map_data(socket)
        return True

    if event == "select_map_symbol":
        # Commit any in-progress river when switching tools
        if socket.context.hex_current_river:
            await _commit_river(socket)
        symbol = payload.get("symbol", "")
        socket.context.hex_active_symbol = symbol
        socket.context.hex_active_overlay = ""
        socket.context.hex_overlay_mode = False
        socket.context.hex_river_drawing = False
        socket.context.hex_notes_mode = False
        socket.context.hex_selected_hex = ""
        socket.context.hex_selected_note = ""
        socket.context.hex_note_html = ""
        socket.context.hex_note_editing = False
        await load_map_data(socket)
        return True

    if event == "toggle_overlays":
        if socket.context.is_keeper:
            socket.context.hex_show_overlays = not socket.context.hex_show_overlays
            await load_map_data(socket)
        return True

    if event == "select_overlay_symbol":
        if socket.context.hex_current_river:
            await _commit_river(socket)
        symbol = payload.get("symbol", "")
        socket.context.hex_active_overlay = symbol
        socket.context.hex_active_symbol = ""
        socket.context.hex_overlay_mode = True
        socket.context.hex_show_overlays = True
        socket.context.hex_river_drawing = False
        socket.context.hex_notes_mode = False
        socket.context.hex_selected_hex = ""
        socket.context.hex_selected_note = ""
        socket.context.hex_note_html = ""
        socket.context.hex_note_editing = False
        await load_map_data(socket)
        return True

    if event == "toggle_notes_mode":
        if socket.context.hex_current_river:
            await _commit_river(socket)
        socket.context.hex_notes_mode = not socket.context.hex_notes_mode
        if socket.context.hex_notes_mode:
            socket.context.hex_active_symbol = ""
            socket.context.hex_active_overlay = ""
            socket.context.hex_overlay_mode = False
            socket.context.hex_river_drawing = False
        else:
            socket.context.hex_selected_hex = ""
            socket.context.hex_selected_note = ""
            socket.context.hex_note_html = ""
            socket.context.hex_note_editing = False
        await load_map_data(socket)
        return True

    if event == "save_hex_note":
        map_id = socket.context.hex_map_id
        hex_key = socket.context.hex_selected_hex
        if not map_id or not hex_key or not socket.context.is_keeper:
            return True
        note_text = payload.get("note", "")
        if isinstance(note_text, list):
            note_text = note_text[0] if note_text else ""

        @sync_to_async(thread_sensitive=False)
        def _save_note():
            hex_map = HexMap.objects.get(pk=map_id)
            notes = hex_map.notes or {}
            if note_text.strip():
                notes[hex_key] = note_text
            else:
                notes.pop(hex_key, None)
            hex_map.notes = notes
            hex_map.save(update_fields=["notes"])

        await _save_note()
        socket.context.hex_selected_hex = ""
        socket.context.hex_selected_note = ""
        socket.context.hex_note_html = ""
        socket.context.hex_note_editing = False
        socket.context.hex_notes_mode = False
        await load_map_data(socket)
        return True

    if event == "edit_hex_note":
        socket.context.hex_note_editing = True
        await load_map_data(socket)
        return True

    if event == "close_hex_note":
        if socket.context.hex_selected_hex:
            socket.context.hex_selected_hex = ""
            socket.context.hex_selected_note = ""
            socket.context.hex_note_html = ""
            socket.context.hex_note_editing = False
            await load_map_data(socket)
        return True

    if event == "hex_click":
        if not socket.context.is_keeper or socket.context.hex_map_edit:
            return True
        col = payload.get("col", "")
        row = payload.get("row", "")
        if col == "" or row == "":
            return True
        target_key = f"{col},{row}"
        current = socket.context.party_location

        # Determine if adjacent
        is_adjacent = False
        if current:
            from cards.ui import get_adjacent_hexes
            cc, cr = map(int, current.split(","))
            adjacent = get_adjacent_hexes(cc, cr)
            is_adjacent = target_key in adjacent
        else:
            # No party placed yet -- treat all hexes as adjacent (placement)
            is_adjacent = True

        if is_adjacent:
            # Show action popup: move or view note
            socket.context.hex_action_hex = target_key
            socket.context.hex_action_is_adjacent = True
            socket.context.hex_selected_hex = ""
            socket.context.hex_note_editing = False
            # Check overlay state for reveal/hide buttons
            map_id = socket.context.hex_map_id
            if map_id:
                @sync_to_async(thread_sensitive=False)
                def _check_overlay():
                    hex_map = HexMap.objects.get(pk=map_id)
                    has_ovl = target_key in (hex_map.overlays or {})
                    is_revealed = target_key in (hex_map.revealed_overlays or {})
                    return has_ovl, is_revealed
                has_ovl, is_revealed = await _check_overlay()
                socket.context.hex_action_has_overlay = has_ovl
                socket.context.hex_action_overlay_revealed = is_revealed
            await load_map_data(socket)
        else:
            # Open note directly
            socket.context.hex_action_hex = ""
            socket.context.hex_action_is_adjacent = False
            map_id = socket.context.hex_map_id
            if map_id:
                @sync_to_async(thread_sensitive=False)
                def _load_note():
                    hex_map = HexMap.objects.get(pk=map_id)
                    notes = hex_map.notes or {}
                    has_ovl = target_key in (hex_map.overlays or {})
                    is_revealed = target_key in (hex_map.revealed_overlays or {})
                    return notes.get(target_key, ""), has_ovl, is_revealed

                note, has_ovl, is_revealed = await _load_note()
                socket.context.hex_selected_hex = target_key
                socket.context.hex_selected_note = note
                socket.context.hex_note_html = render_markdown_safe(note) if note.strip() else ""
                socket.context.hex_note_editing = False
                socket.context.hex_action_has_overlay = has_ovl
                socket.context.hex_action_overlay_revealed = is_revealed
                await load_map_data(socket)
        return True

    if event == "hex_action_move":
        if not socket.context.is_keeper:
            return True
        target_key = socket.context.hex_action_hex
        if not target_key:
            return True
        socket.context.hex_action_hex = ""
        socket.context.hex_action_is_adjacent = False
        # Reuse move_party logic
        col, row = target_key.split(",")
        payload = {"col": col, "row": row}
        # Fall through to move_party below

    if event == "hex_action_note":
        if not socket.context.is_keeper:
            return True
        target_key = socket.context.hex_action_hex
        if not target_key:
            return True
        socket.context.hex_action_hex = ""
        socket.context.hex_action_is_adjacent = False
        map_id = socket.context.hex_map_id
        if map_id:
            @sync_to_async(thread_sensitive=False)
            def _load_note():
                hex_map = HexMap.objects.get(pk=map_id)
                notes = hex_map.notes or {}
                return notes.get(target_key, "")

            note = await _load_note()
            socket.context.hex_selected_hex = target_key
            socket.context.hex_selected_note = note
            socket.context.hex_note_html = render_markdown_safe(note) if note.strip() else ""
            socket.context.hex_note_editing = False
            await load_map_data(socket)
        return True

    if event == "reveal_overlay":
        if not socket.context.is_keeper:
            return True
        target_key = socket.context.hex_action_hex or socket.context.hex_selected_hex
        map_id = socket.context.hex_map_id
        if not target_key or not map_id:
            return True

        @sync_to_async(thread_sensitive=False)
        def _reveal():
            hex_map = HexMap.objects.get(pk=map_id)
            ovl = (hex_map.overlays or {}).get(target_key)
            if ovl:
                revealed = hex_map.revealed_overlays or {}
                revealed[target_key] = ovl
                hex_map.revealed_overlays = revealed
                hex_map.save(update_fields=["revealed_overlays"])

        await _reveal()
        socket.context.hex_action_hex = ""
        socket.context.hex_action_is_adjacent = False
        socket.context.hex_selected_hex = ""
        await load_map_data(socket)
        await _broadcast(socket, HexMap)
        return True

    if event == "hide_overlay":
        if not socket.context.is_keeper:
            return True
        target_key = socket.context.hex_action_hex or socket.context.hex_selected_hex
        map_id = socket.context.hex_map_id
        if not target_key or not map_id:
            return True

        @sync_to_async(thread_sensitive=False)
        def _hide():
            hex_map = HexMap.objects.get(pk=map_id)
            revealed = hex_map.revealed_overlays or {}
            if target_key in revealed:
                del revealed[target_key]
                hex_map.revealed_overlays = revealed
                hex_map.save(update_fields=["revealed_overlays"])

        await _hide()
        socket.context.hex_action_hex = ""
        socket.context.hex_action_is_adjacent = False
        socket.context.hex_selected_hex = ""
        await load_map_data(socket)
        await _broadcast(socket, HexMap)
        return True

    if event == "close_hex_action":
        socket.context.hex_action_hex = ""
        socket.context.hex_action_is_adjacent = False
        await load_map_data(socket)
        return True

    # --- Site Map Events ---

    if event == "open_site_map":
        hex_key = socket.context.hex_selected_hex or socket.context.hex_action_hex
        if not hex_key or not socket.context.is_keeper:
            return True
        map_id = socket.context.hex_map_id
        if not map_id:
            return True

        @sync_to_async(thread_sensitive=False)
        def _load_site_map():
            hex_map = HexMap.objects.get(pk=map_id)
            site_maps = hex_map.site_maps or {}
            return site_maps.get(hex_key, {"nodes": {}, "routes": [], "entrances": []})

        site_data = await _load_site_map()
        socket.context.site_map_open = True
        socket.context.site_map_hex = hex_key
        socket.context.site_map_data = site_data
        socket.context.site_map_edit = False
        socket.context.site_map_tool = ""
        socket.context.site_map_route_from = -1
        socket.context.site_map_selected_type = ""
        socket.context.site_map_selected_id = ""
        socket.context.site_map_detail_name = ""
        socket.context.site_map_detail_notes = ""
        socket.context.site_map_detail_editing = ""
        socket.context.site_map_detail_draft = ""
        from cards.ui import render_site_map_svg
        socket.context.site_map_svg = render_site_map_svg(site_data)
        await load_map_data(socket)
        return True

    if event == "close_site_map":
        socket.context.site_map_open = False
        socket.context.site_map_hex = ""
        socket.context.site_map_data = {}
        socket.context.site_map_svg = ""
        socket.context.site_map_edit = False
        socket.context.site_map_tool = ""
        socket.context.site_map_route_from = -1
        socket.context.site_map_selected_type = ""
        socket.context.site_map_selected_id = ""
        socket.context.site_map_detail_editing = ""
        socket.context.site_map_detail_draft = ""
        await load_map_data(socket)
        return True

    if event == "toggle_site_map_edit":
        if not socket.context.is_keeper:
            return True
        socket.context.site_map_edit = not socket.context.site_map_edit
        socket.context.site_map_tool = ""
        socket.context.site_map_route_from = -1
        socket.context.site_map_selected_type = ""
        socket.context.site_map_selected_id = ""
        socket.context.site_map_detail_editing = ""
        socket.context.site_map_detail_draft = ""
        await load_map_data(socket)
        return True

    if event == "set_site_map_tool":
        tool = payload.get("tool", "")
        # Toggle off if same tool clicked again
        if socket.context.site_map_tool == tool:
            socket.context.site_map_tool = ""
        else:
            socket.context.site_map_tool = tool
        socket.context.site_map_route_from = -1
        socket.context.site_map_selected_type = ""
        socket.context.site_map_selected_id = ""
        socket.context.site_map_detail_editing = ""
        await load_map_data(socket)
        return True

    if event == "site_map_click":
        if not socket.context.site_map_open or not socket.context.is_keeper:
            return True
        click_type = payload.get("type", "")  # "node", "empty_node", "route", "entrance"
        click_id = payload.get("id", "")

        if socket.context.site_map_edit:
            await _handle_site_map_edit_click(socket, click_type, click_id)
        else:
            # View mode: select element for detail
            await _handle_site_map_view_click(socket, click_type, click_id)
        await load_map_data(socket)
        return True

    if event == "site_map_start_edit":
        field = payload.get("field", "")
        if field == "name":
            socket.context.site_map_detail_editing = "name"
            socket.context.site_map_detail_draft = socket.context.site_map_detail_name
        elif field == "notes":
            socket.context.site_map_detail_editing = "notes"
            socket.context.site_map_detail_draft = socket.context.site_map_detail_notes
        await load_map_data(socket)
        return True

    if event == "site_map_update_draft":
        socket.context.site_map_detail_draft = payload.get("value", "")
        return True

    if event == "site_map_save_edit":
        field = socket.context.site_map_detail_editing
        value = socket.context.site_map_detail_draft
        sel_type = socket.context.site_map_selected_type
        sel_id = socket.context.site_map_selected_id
        data = socket.context.site_map_data

        if sel_type == "node" and sel_id in data.get("nodes", {}):
            data["nodes"][sel_id][field] = value
            if field == "name":
                socket.context.site_map_detail_name = value
            else:
                socket.context.site_map_detail_notes = value
        elif sel_type == "route":
            for r in data.get("routes", []):
                from cards.ui import _sm_route_key
                if _sm_route_key(r["from"], r["to"]) == sel_id:
                    r[field] = value
                    if field == "name":
                        socket.context.site_map_detail_name = value
                    else:
                        socket.context.site_map_detail_notes = value
                    break
        elif sel_type == "entrance":
            for e in data.get("entrances", []):
                if str(e["node"]) == sel_id:
                    e[field] = value
                    if field == "name":
                        socket.context.site_map_detail_name = value
                    else:
                        socket.context.site_map_detail_notes = value
                    break

        socket.context.site_map_detail_editing = ""
        socket.context.site_map_detail_draft = ""
        await _save_site_map_data(socket)
        await load_map_data(socket)
        return True

    if event == "site_map_cancel_edit":
        socket.context.site_map_detail_editing = ""
        socket.context.site_map_detail_draft = ""
        await load_map_data(socket)
        return True

    if event == "move_party" or event == "hex_action_move":
        if not socket.context.is_keeper or socket.context.hex_map_edit:
            return True
        col = payload.get("col", "")
        row = payload.get("row", "")
        if col == "" or row == "":
            return True
        target_key = f"{col},{row}"
        current = socket.context.party_location

        if current:
            from cards.ui import get_adjacent_hexes
            cc, cr = map(int, current.split(","))
            adjacent = get_adjacent_hexes(cc, cr)
            if target_key not in adjacent:
                return True

        map_id = socket.context.hex_map_id
        if not map_id:
            return True

        @sync_to_async(thread_sensitive=False)
        def _move():
            hex_map = HexMap.objects.get(pk=map_id)
            if hex_map.party_location:
                trail = hex_map.party_trail or []
                trail.append(hex_map.party_location)
                hex_map.party_trail = trail
            hex_map.party_location = target_key
            hex_map.save(update_fields=["party_location", "party_trail"])

        await _move()
        await load_map_data(socket)
        await _broadcast(socket, HexMap)
        return True

    # --- Map create dialog ---

    if event == "open_map_create":
        sit_type = payload.get("type", "note")
        socket.context.map_create_open = True
        socket.context.map_create_type = sit_type
        socket.context.map_create_name = ""
        socket.context.map_create_notes = ""
        socket.context.map_create_error = ""
        return True

    if event == "map_cancel_create":
        socket.context.map_create_open = False
        socket.context.map_create_type = ""
        socket.context.map_create_name = ""
        socket.context.map_create_notes = ""
        socket.context.map_create_error = ""
        return True

    if event == "map_update_create":
        name = payload.get("name", "")
        if isinstance(name, list):
            name = name[0] if name else ""
        socket.context.map_create_name = name
        notes = payload.get("notes", "")
        if isinstance(notes, list):
            notes = notes[0] if notes else ""
        socket.context.map_create_notes = notes
        return True

    if event == "map_save_create":
        name = socket.context.map_create_name.strip()
        notes = socket.context.map_create_notes.strip()
        sit_type = socket.context.map_create_type or "note"
        if not name:
            socket.context.map_create_error = "Name is required"
            return True
        game_id = socket.context.frame.get("game_id")
        if not game_id:
            return True

        if sit_type == "keeper_note":
            @sync_to_async(thread_sensitive=False)
            def _create_keeper_note():
                KeeperNote = apps.get_model('cards', 'KeeperNote')
                return KeeperNote.objects.create(
                    name=name, notes=notes, game_id=game_id,
                )
            await _create_keeper_note()
        else:
            @sync_to_async(thread_sensitive=False)
            def _create_entry():
                Situation = apps.get_model('cards', 'Situation')
                Game = apps.get_model('cards', 'Game')
                Hand = apps.get_model('cards', 'Hand')
                loc = ""
                hm = HexMap.objects.filter(game_id=game_id).first()
                if hm and hm.party_location:
                    loc = hm.party_location
                game = Game.objects.get(pk=game_id)
                entry = Situation.objects.create(
                    name=name, notes=notes, game_id=game_id,
                    situation_type=sit_type, location=loc,
                    game_time=game.game_time or {},
                )
                # Lock drawing for all players when a situation starts
                if sit_type == "situation":
                    Hand.objects.filter(
                        character__game_id=game_id
                    ).update(draw_active=False)
                return entry
            await _create_entry()
        socket.context.map_create_open = False
        socket.context.map_create_type = ""
        socket.context.map_create_name = ""
        socket.context.map_create_notes = ""
        socket.context.map_create_error = ""
        await load_map_data(socket)
        await _broadcast(socket, HexMap)
        return True

    # --- Time advance ---

    if event == "open_time_advance":
        if not socket.context.is_keeper:
            return True
        game_id = socket.context.frame.get("game_id")
        if not game_id:
            return True

        @sync_to_async(thread_sensitive=False)
        def _get_game_time():
            Game = apps.get_model('cards', 'Game')
            return Game.objects.get(pk=game_id).game_time or {}

        current = await _get_game_time()
        from cards.models.game import advance_shift, SEASONS, SHIFTS
        advanced = advance_shift(current) if current else {
            "age": "", "year": 1, "season": "spring", "day": 1, "shift": "morning",
        }
        socket.context.time_advance_age = advanced.get("age", "")
        socket.context.time_advance_year = str(advanced.get("year", 1))
        socket.context.time_advance_season = advanced.get("season", "spring")
        socket.context.time_advance_day = str(advanced.get("day", 1))
        socket.context.time_advance_shift = advanced.get("shift", "morning")
        socket.context.time_advance_open = True
        return True

    if event == "time_advance_update":
        if not socket.context.is_keeper:
            return True
        for key in ("age", "year", "season", "day", "shift"):
            val = payload.get(key)
            if val is not None:
                if isinstance(val, list):
                    val = val[0]
                setattr(socket.context, f"time_advance_{key}", val)
        return True

    if event == "time_advance_next":
        if not socket.context.is_keeper:
            return True
        field = payload.get("field", "")
        if isinstance(field, list):
            field = field[0]
        from cards.models.game import SEASONS, SHIFTS
        if field == "year":
            try:
                y = int(socket.context.time_advance_year)
            except (ValueError, TypeError):
                y = 1
            socket.context.time_advance_year = str(y + 1)
        elif field == "season":
            idx = SEASONS.index(socket.context.time_advance_season) if socket.context.time_advance_season in SEASONS else 0
            if idx + 1 < len(SEASONS):
                socket.context.time_advance_season = SEASONS[idx + 1]
            else:
                socket.context.time_advance_season = SEASONS[0]
                try:
                    y = int(socket.context.time_advance_year)
                except (ValueError, TypeError):
                    y = 1
                socket.context.time_advance_year = str(y + 1)
            socket.context.time_advance_day = "1"
        elif field == "day":
            try:
                d = int(socket.context.time_advance_day)
            except (ValueError, TypeError):
                d = 1
            socket.context.time_advance_day = str(d + 1)
        elif field == "shift":
            idx = SHIFTS.index(socket.context.time_advance_shift) if socket.context.time_advance_shift in SHIFTS else 0
            if idx + 1 < len(SHIFTS):
                socket.context.time_advance_shift = SHIFTS[idx + 1]
            else:
                socket.context.time_advance_shift = SHIFTS[0]
                try:
                    d = int(socket.context.time_advance_day)
                except (ValueError, TypeError):
                    d = 1
                socket.context.time_advance_day = str(d + 1)
        return True

    if event == "time_advance_save":
        if not socket.context.is_keeper:
            return True
        game_id = socket.context.frame.get("game_id")
        if not game_id:
            return True
        try:
            year_val = int(socket.context.time_advance_year)
        except (ValueError, TypeError):
            year_val = 1
        try:
            day_val = int(socket.context.time_advance_day)
        except (ValueError, TypeError):
            day_val = 1
        new_time = {
            "age": socket.context.time_advance_age,
            "year": year_val,
            "season": socket.context.time_advance_season,
            "day": day_val,
            "shift": socket.context.time_advance_shift,
        }

        @sync_to_async(thread_sensitive=False)
        def _save_time():
            Game = apps.get_model('cards', 'Game')
            Game.objects.filter(pk=game_id).update(game_time=new_time)

        await _save_time()
        socket.context.time_advance_open = False
        from cards.models.game import format_time
        socket.context.current_game_time = format_time(new_time)
        await _broadcast(socket, HexMap)
        return True

    if event == "time_advance_cancel":
        socket.context.time_advance_open = False
        return True

    # --- Copy map ---

    if event == "open_copy_map":
        if not socket.context.is_keeper:
            return True
        game_id = socket.context.frame.get("game_id")
        if not game_id:
            return True

        @sync_to_async(thread_sensitive=False)
        def _get_games():
            Game = apps.get_model('cards', 'Game')
            return list(
                Game.objects.exclude(pk=game_id)
                .order_by('name')
                .values('pk', 'name')
            )

        games = await _get_games()
        socket.context.copy_map_games = [
            {"id": str(g["pk"]), "name": g["name"]} for g in games
        ]
        socket.context.copy_map_target = ""
        socket.context.copy_map_error = ""
        socket.context.copy_map_open = True
        return True

    if event == "copy_map_update":
        val = payload.get("target", "")
        if isinstance(val, list):
            val = val[0]
        socket.context.copy_map_target = val
        return True

    if event == "copy_map_save":
        if not socket.context.is_keeper:
            return True
        target_id = socket.context.copy_map_target
        if not target_id:
            socket.context.copy_map_error = "Select a target game"
            return True
        map_id = socket.context.hex_map_id
        if not map_id:
            return True

        @sync_to_async(thread_sensitive=False)
        def _copy():
            src = HexMap.objects.get(pk=map_id)
            # Delete existing map in target game if any
            HexMap.objects.filter(game_id=int(target_id)).delete()
            HexMap.objects.create(
                name=src.name,
                game_id=int(target_id),
                hexes=src.hexes or {},
                rivers=src.rivers or [],
                overlays=src.overlays or {},
                barriers=src.barriers or {},
            )

        await _copy()
        socket.context.copy_map_open = False
        return True

    if event == "copy_map_cancel":
        socket.context.copy_map_open = False
        return True

    if event == "cancel_map_situation":
        situation_id = socket.context.hand_active_situation_id
        if situation_id and socket.context.is_keeper and not socket.context.situation_dice:
            @sync_to_async(thread_sensitive=False)
            def _cancel():
                Situation = apps.get_model('cards', 'Situation')
                sit = Situation.objects.get(pk=situation_id)
                if sit.dice:
                    return  # Don't cancel after roll
                sit.delete()

            await _cancel()
            socket.context.hand_active_situation_id = None
            socket.context.active_situation_name = ""
            socket.context.active_situation_notes = ""
            socket.context.situation_cards = []
            socket.context.situation_dice = []
            socket.context.situation_assignments = {}
            socket.context.situation_dice_assigned = False
            socket.context.situation_resolved = False
            socket.context.situation_all_assigned = False
            socket.context.map_situation_active = False
            await load_map_data(socket)
            if socket.context.hand_is_player:
                await load_hand_data(socket)
            await _broadcast(socket, HexMap)
        return True

    # --- Map detail popup ---

    if event == "open_map_detail":
        entry_id = payload.get("id", "")
        if not entry_id:
            return True
        # Close previous detail (release locks)
        await _close_map_detail(socket)
        socket.context.map_detail = {"id": entry_id}
        await _refresh_map_detail(socket)
        return True

    if event == "close_map_detail":
        had_editing = bool(socket.context.map_detail_editing)
        await _close_map_detail(socket)
        if had_editing:
            await _broadcast(socket, HexMap)
        return True

    if event == "map_start_edit":
        field_name = payload.get("field", "")
        detail_id = (socket.context.map_detail or {}).get("id", "")
        if not field_name or not detail_id:
            return True

        sid = socket.context.session_id
        if acquire_lock("cards.situation", detail_id, field_name, sid):
            @sync_to_async(thread_sensitive=False)
            def _get_value():
                Situation = apps.get_model('cards', 'Situation')
                try:
                    s = Situation.objects.get(pk=detail_id)
                    return getattr(s, field_name, "")
                except Situation.DoesNotExist:
                    return ""

            val = await _get_value()
            socket.context.map_detail_editing = field_name
            socket.context.map_detail_draft = str(val) if val else ""
            await _broadcast(socket, HexMap)
        await _refresh_map_detail(socket)
        return True

    if event == "map_update_draft":
        value = payload.get("value", "")
        if isinstance(value, list):
            value = value[0] if value else ""
        socket.context.map_detail_draft = value
        return True

    if event == "map_cancel_edit":
        detail_id = (socket.context.map_detail or {}).get("id", "")
        field_name = socket.context.map_detail_editing
        if detail_id and field_name:
            release_lock("cards.situation", detail_id, field_name,
                         socket.context.session_id)
        socket.context.map_detail_editing = ""
        socket.context.map_detail_draft = ""
        await _refresh_map_detail(socket)
        await _broadcast(socket, HexMap)
        return True

    if event == "map_save_edit":
        detail_id = (socket.context.map_detail or {}).get("id", "")
        field_name = socket.context.map_detail_editing
        value = socket.context.map_detail_draft
        if not detail_id or not field_name:
            return True

        sid = socket.context.session_id
        if get_lock_holder("cards.situation", detail_id, field_name) != sid:
            socket.context.map_detail_editing = ""
            socket.context.map_detail_draft = ""
            await _refresh_map_detail(socket)
            return True

        @sync_to_async(thread_sensitive=False)
        def _save_field():
            Situation = apps.get_model('cards', 'Situation')
            try:
                s = Situation.objects.get(pk=detail_id)
                setattr(s, field_name, value)
                s.save(update_fields=[field_name])
            except Situation.DoesNotExist:
                pass

        await _save_field()
        release_lock("cards.situation", detail_id, field_name, sid)
        socket.context.map_detail_editing = ""
        socket.context.map_detail_draft = ""
        await _refresh_map_detail(socket)
        await load_map_data(socket)
        await _broadcast(socket, HexMap)
        return True

    # --- River drawing ---

    if event == "start_river":
        # Commit previous river if any, then enter river drawing mode
        if socket.context.hex_current_river:
            await _commit_river(socket)
        socket.context.hex_river_drawing = True
        socket.context.hex_active_symbol = ""
        socket.context.hex_active_overlay = ""
        socket.context.hex_overlay_mode = False
        socket.context.hex_notes_mode = False
        socket.context.hex_selected_hex = ""
        socket.context.hex_selected_note = ""
        socket.context.hex_note_html = ""
        socket.context.hex_note_editing = False
        socket.context.hex_current_river = []
        await load_map_data(socket)
        return True

    if event == "finish_river":
        if socket.context.hex_current_river:
            await _commit_river(socket)
        socket.context.hex_current_river = []
        socket.context.hex_river_drawing = False
        await load_map_data(socket)
        return True

    if event == "undo_river_point":
        if socket.context.hex_current_river:
            socket.context.hex_current_river = socket.context.hex_current_river[:-1]
            await load_map_data(socket)
        return True

    if event == "delete_last_river":
        map_id = socket.context.hex_map_id
        if map_id and socket.context.is_keeper:
            @sync_to_async(thread_sensitive=False)
            def _delete():
                hex_map = HexMap.objects.get(pk=map_id)
                rivers = hex_map.rivers or []
                if rivers:
                    rivers.pop()
                    hex_map.rivers = rivers
                    hex_map.save(update_fields=["rivers"])

            await _delete()
            await load_map_data(socket)
            await _broadcast(socket, HexMap)
        return True

    # --- Hex painting ---

    if event == "set_hex":
        map_id = socket.context.hex_map_id
        if not map_id or not socket.context.is_keeper or not socket.context.hex_map_edit:
            return True
        col = payload.get("col", "")
        row = payload.get("row", "")
        if col == "" or row == "":
            return True
        key = f"{col},{row}"

        # Notes mode: select hex and load its note
        if socket.context.hex_notes_mode:
            @sync_to_async(thread_sensitive=False)
            def _load_note():
                hex_map = HexMap.objects.get(pk=map_id)
                notes = hex_map.notes or {}
                return notes.get(key, "")

            note = await _load_note()
            socket.context.hex_selected_hex = key
            socket.context.hex_selected_note = note
            socket.context.hex_note_html = render_markdown_safe(note) if note.strip() else ""
            socket.context.hex_note_editing = False
            await load_map_data(socket)
            return True

        # River drawing mode: add hex to current river
        if socket.context.hex_river_drawing:
            from cards.ui import _find_shared_edge
            current = socket.context.hex_current_river
            if current:
                # Validate adjacency
                lc, lr = map(int, current[-1].split(","))
                edge = _find_shared_edge(lc, lr, int(col), int(row))
                if edge is None:
                    return True  # not adjacent, ignore
            socket.context.hex_current_river = current + [key]
            await load_map_data(socket)
            return True

        # Overlay painting mode
        if socket.context.hex_overlay_mode:
            overlay = socket.context.hex_active_overlay

            # Barrier tool
            if overlay and overlay.startswith("barrier_"):
                barrier_arg = overlay.split("_", 1)[1]

                @sync_to_async(thread_sensitive=False)
                def _toggle_barrier():
                    hex_map = HexMap.objects.get(pk=map_id)
                    barriers = hex_map.barriers or {}
                    edges = barriers.get(key, [])
                    if barrier_arg == "eraser":
                        # Remove all barriers from this hex
                        barriers.pop(key, None)
                    else:
                        edge_i = int(barrier_arg)
                        if edge_i in edges:
                            edges.remove(edge_i)
                        else:
                            edges.append(edge_i)
                        if edges:
                            barriers[key] = edges
                        else:
                            barriers.pop(key, None)
                    hex_map.barriers = barriers
                    hex_map.save(update_fields=["barriers"])

                await _toggle_barrier()
                await load_map_data(socket)
                return True

            # Regular overlay symbol
            @sync_to_async(thread_sensitive=False)
            def _set_overlay():
                hex_map = HexMap.objects.get(pk=map_id)
                overlays = hex_map.overlays or {}
                if overlay:
                    overlays[key] = overlay
                else:
                    overlays.pop(key, None)
                hex_map.overlays = overlays
                hex_map.save(update_fields=["overlays"])

            await _set_overlay()
            await load_map_data(socket)
            return True

        # Normal symbol painting mode
        symbol = socket.context.hex_active_symbol

        @sync_to_async(thread_sensitive=False)
        def _set_hex():
            hex_map = HexMap.objects.get(pk=map_id)
            hexes = hex_map.hexes or {}
            if symbol:
                hexes[key] = symbol
            else:
                hexes.pop(key, None)
            hex_map.hexes = hexes
            hex_map.save(update_fields=["hexes"])

        await _set_hex()
        await load_map_data(socket)
        await _broadcast(socket, HexMap)
        return True

    # --- Situation dice ---

    if event == "roll_situation":
        situation_id = socket.context.hand_active_situation_id
        if situation_id:
            @sync_to_async(thread_sensitive=False)
            def _roll():
                Situation = apps.get_model('cards', 'Situation')
                Hand = apps.get_model('cards', 'Hand')
                SituationCard = apps.get_model('cards', 'SituationCard')
                Game = apps.get_model('cards', 'Game')
                sit = Situation.objects.get(pk=situation_id)
                if sit.dice:
                    return  # Already rolled
                originals = list(
                    sit.cards.select_related('card', 'character').all()
                )
                n = len(originals)
                if n == 0:
                    return
                dice = [random.randint(1, 6) for _ in range(n)]
                sit.dice = dice
                sit.save(update_fields=["dice"])
                # Create archived snapshot cards on the situation
                for cc in originals:
                    SituationCard.objects.create(
                        situation=sit,
                        name=cc.card.name,
                        notes=cc.card.notes or "",
                        level=cc.level,
                        character_name=cc.character.name if cc.character else "",
                    )
                # Clear the M2M (snapshots replace it)
                sit.cards.clear()
                # Remove originals from their owners' hands
                for cc in originals:
                    for hand in Hand.objects.filter(cards__pk=cc.pk):
                        hand.cards.remove(cc.pk)
                # Re-enable drawing for hands with no non-attribute cards left
                affected_character_ids = set(cc.character_id for cc in originals)
                for char_id in affected_character_ids:
                    for hand in Hand.objects.filter(character_id=char_id):
                        has_non_attr = hand.cards.exclude(
                            tag__name="Attribute"
                        ).exists()
                        if not has_non_attr:
                            hand.draw_active = True
                            hand.save(update_fields=["draw_active"])

            await _roll()
            await _refresh(socket)
            if socket.context.hand_is_player:
                await load_hand_data(socket)
            await _broadcast(socket, HexMap)
        return True

    if event == "assign_die":
        card_id = payload.get("card_id", "")
        die_index = payload.get("die_index", "")
        situation_id = socket.context.hand_active_situation_id
        if card_id and die_index != "" and situation_id:
            @sync_to_async(thread_sensitive=False)
            def _assign():
                Situation = apps.get_model('cards', 'Situation')
                sit = Situation.objects.get(pk=situation_id)
                if not sit.dice or sit.dice_assigned:
                    return
                assignments = sit.assignments or {}
                assignments[str(card_id)] = int(die_index)
                sit.assignments = assignments
                sit.save(update_fields=["assignments"])

            await _assign()
            await _refresh(socket)
            if socket.context.hand_is_player:
                await load_hand_data(socket)
            await _broadcast(socket, HexMap)
        return True

    if event == "unassign_die":
        card_id = payload.get("card_id", "")
        situation_id = socket.context.hand_active_situation_id
        if card_id and situation_id:
            @sync_to_async(thread_sensitive=False)
            def _unassign():
                Situation = apps.get_model('cards', 'Situation')
                sit = Situation.objects.get(pk=situation_id)
                if sit.dice_assigned:
                    return
                assignments = sit.assignments or {}
                assignments.pop(str(card_id), None)
                sit.assignments = assignments
                sit.save(update_fields=["assignments"])

            await _unassign()
            await _refresh(socket)
            if socket.context.hand_is_player:
                await load_hand_data(socket)
            await _broadcast(socket, HexMap)
        return True

    if event == "lock_dice":
        situation_id = socket.context.hand_active_situation_id
        if situation_id:
            @sync_to_async(thread_sensitive=False)
            def _lock():
                Situation = apps.get_model('cards', 'Situation')
                Game = apps.get_model('cards', 'Game')
                sit = Situation.objects.get(pk=situation_id)
                if not sit.dice or sit.dice_assigned:
                    return
                card_count = sit.situation_cards.count()
                if len(sit.assignments or {}) < card_count:
                    return
                sit.dice_assigned = True
                sit.save(update_fields=["dice_assigned"])

            await _lock()
            await _refresh(socket)
            await _broadcast(socket, HexMap)
        return True

    if event == "toggle_used_card":
        card_id = payload.get("card_id", "")
        situation_id = socket.context.hand_active_situation_id
        if card_id and situation_id and socket.context.situation_dice_assigned:
            @sync_to_async(thread_sensitive=False)
            def _toggle_used():
                SituationCard = apps.get_model('cards', 'SituationCard')
                sc = SituationCard.objects.get(pk=int(card_id), situation_id=situation_id)
                sc.used = not sc.used
                sc.save(update_fields=["used"])

            await _toggle_used()
            await _refresh(socket)
            await _broadcast(socket, HexMap)
        return True

    if event == "resolve_situation":
        situation_id = socket.context.hand_active_situation_id
        if not situation_id:
            return True

        @sync_to_async(thread_sensitive=False)
        def _resolve():
            Situation = apps.get_model('cards', 'Situation')
            sit = Situation.objects.filter(pk=situation_id, resolved=False).first()
            if sit:
                sit.resolved = True
                sit.save(update_fields=["resolved"])

        await _resolve()
        await _refresh(socket)
        await _broadcast(socket, HexMap)
        return True

    # --- Search modal ---

    if event == "open_search":
        if not socket.context.is_keeper:
            return True
        socket.context.search_open = True
        socket.context.search_query = ""
        socket.context.search_results = []
        return True

    if event == "close_search":
        socket.context.search_open = False
        socket.context.search_query = ""
        socket.context.search_results = []
        return True

    if event == "search_update":
        query = (payload.get("value") or "").strip()
        socket.context.search_query = query
        if len(query) < 2:
            socket.context.search_results = []
            return True
        game_id = socket.context.frame.get("game_id")
        if not game_id:
            return True

        @sync_to_async(thread_sensitive=False)
        def _run_search():
            Situation = apps.get_model('cards', 'Situation')
            Card = apps.get_model('cards', 'Card')
            q = query.lower()
            results = []
            # 1. Hex map notes
            first_note = True
            hm = HexMap.objects.filter(game_id=game_id).first()
            if hm and hm.notes:
                for key, note in hm.notes.items():
                    if note and q in note.lower():
                        if first_note:
                            results.append({"group_label": "Map Notes", "type": "", "id": "", "badge": "", "label": "", "snippet": ""})
                            first_note = False
                        results.append({
                            "group_label": "",
                            "type": "hex_note",
                            "id": key,
                            "badge": "Map",
                            "label": f"Hex {key}",
                            "snippet": _snippet(note, query),
                        })
            # 2. Situations
            first_sit = True
            for sit in Situation.objects.filter(game_id=game_id):
                text = f"{sit.name} {sit.notes or ''}"
                if q in text.lower():
                    if first_sit:
                        results.append({"group_label": "Situations", "type": "", "id": "", "badge": "", "label": "", "snippet": ""})
                        first_sit = False
                    snippet = ""
                    if sit.notes and q in sit.notes.lower():
                        snippet = _snippet(sit.notes, query)
                    results.append({
                        "group_label": "",
                        "type": "situation",
                        "id": str(sit.pk),
                        "badge": "Situation",
                        "label": sit.name,
                        "snippet": snippet,
                    })
            # 3. Characters
            first_char = True
            Character = apps.get_model('cards', 'Character')
            for char in Character.objects.filter(game_id=game_id):
                text = f"{char.name} {char.notes or ''}"
                if q in text.lower():
                    if first_char:
                        results.append({"group_label": "Characters", "type": "", "id": "", "badge": "", "label": "", "snippet": ""})
                        first_char = False
                    snippet = ""
                    if char.notes and q in char.notes.lower():
                        snippet = _snippet(char.notes, query)
                    results.append({
                        "group_label": "",
                        "type": "character",
                        "id": str(char.pk),
                        "badge": "Character",
                        "label": char.name,
                        "snippet": snippet,
                    })
            # 4. Cards (via characters in this game)
            first_card = True
            seen_cards = set()
            from cards.models.character_card import CharacterCard
            for cc in (CharacterCard.objects
                       .filter(character__game_id=game_id)
                       .select_related('card', 'character')):
                card = cc.card
                if card.pk in seen_cards:
                    continue
                text = f"{card.name} {card.notes or ''}"
                if q in text.lower():
                    seen_cards.add(card.pk)
                    if first_card:
                        results.append({"group_label": "Cards", "type": "", "id": "", "badge": "", "label": "", "snippet": ""})
                        first_card = False
                    snippet = ""
                    if card.notes and q in card.notes.lower():
                        snippet = _snippet(card.notes, query)
                    results.append({
                        "group_label": "",
                        "type": "card",
                        "id": str(cc.character_id),
                        "badge": "Card",
                        "label": f"{card.name} ({cc.character.name})",
                        "snippet": snippet,
                    })
            return results

        socket.context.search_results = await _run_search()
        return True

    if event == "search_select":
        result_type = payload.get("type", "")
        result_id = payload.get("id", "")
        if not result_type or not result_id:
            return True
        # Close search
        socket.context.search_open = False
        socket.context.search_query = ""
        socket.context.search_results = []
        if result_type == "hex_note":
            # Open hex note popup
            target_key = result_id
            map_id = socket.context.hex_map_id
            if map_id:
                @sync_to_async(thread_sensitive=False)
                def _load_note():
                    hex_map = HexMap.objects.get(pk=map_id)
                    notes = hex_map.notes or {}
                    return notes.get(target_key, "")

                note = await _load_note()
                socket.context.hex_selected_hex = target_key
                socket.context.hex_selected_note = note
                socket.context.hex_note_html = render_markdown_safe(note) if note.strip() else ""
                socket.context.hex_note_editing = False
                await load_map_data(socket)
        elif result_type == "situation":
            socket.context.map_detail = {"id": result_id}
            await _refresh_map_detail(socket)
        elif result_type == "character":
            await socket.push_navigate("/alive/character/", {"detail": result_id})
        elif result_type == "card":
            # Navigate to the character that owns the card
            await socket.push_navigate("/alive/character/", {"detail": result_id})
        return True

    # --- Quick dice rolls (sidebar) ---

    if event == "quick_roll_d6":
        from cards.ui import render_die_svg
        v = random.randint(1, 6)
        socket.context.quick_d6 = v
        socket.context.quick_d6_svg = render_die_svg(v, css_class="h-8 w-8")
        return True

    if event == "quick_roll_d12":
        socket.context.quick_d12 = random.randint(1, 12)
        return True

    # Not a cardplay event
    return False


# --- Mount Hook ---

async def cardplay_mount_hook(socket, session):
    """Set up cardplay-specific state during mount.

    CardplayContext provides defaults for all fields. This hook sets
    the computed values that depend on the current session.
    """
    ctx = socket.context
    player_role = session.get("player_role")
    character_id = session.get("character_id")
    hand_is_player = player_role == "player" and character_id is not None

    ctx.hand_is_player = hand_is_player
    ctx.hand_character_id = character_id if hand_is_player else None
    ctx.is_keeper = player_role == "keeper"
    ctx.keeper_character_id = character_id if player_role == "keeper" else None

    from cards.ui import render_die_svg
    ctx.quick_d6_svg = render_die_svg(ctx.quick_d6, css_class="h-8 w-8")

    Character = apps.get_model('cards', 'Character')
    ctx.has_sheet_defaults = hasattr(Character, 'sheet') and hasattr(Character.sheet, 'field')

    if hand_is_player:
        await load_hand_data(socket)
        if ctx.situation_dice:
            ctx.hand_collapsed = True


# --- Params Hook ---

def _make_params_hook(conf_template):
    async def cardplay_params_hook(socket, url, params):
        """Load cardplay data after URL params are processed."""
        is_situation = conf_template == "situation.html"
        is_map = conf_template == "map.html"
        if is_situation or is_map:
            await load_situation_data(socket, is_situation, is_map)
        if is_map:
            await load_map_data(socket)
    return cardplay_params_hook


# --- Refresh Hook ---

def _make_refresh_hook(conf_template):
    async def cardplay_refresh_hook(socket):
        """Refresh cardplay data after items are rebuilt."""
        is_situation = conf_template == "situation.html"
        is_map = conf_template == "map.html"
        if is_situation or is_map:
            await load_situation_data(socket, is_situation, is_map)
        if is_map:
            await load_map_data(socket)
        if socket.context.hand_is_player:
            await load_hand_data(socket)
    return cardplay_refresh_hook


# --- Info Hook ---

async def cardplay_info_hook(event, socket):
    """Handle Card channel events for hand footer updates."""
    if not socket.context.hand_is_player:
        return
    Card = apps.get_model('cards', 'Card')
    card_channel = get_store(Card).channel
    if event.name == card_channel:
        data = event.payload
        action = data.get("action", "")
        if action in ("state_changed", "locks_released", "item_created", "item_deleted"):
            await _refresh(socket)


# --- Extra Subscriptions ---

async def cardplay_extra_subscriptions(socket):
    """Subscribe to Card channel for hand footer updates."""
    channels = []
    if socket.context.hand_is_player:
        Card = apps.get_model('cards', 'Card')
        channels.append(get_store(Card).channel)
    return channels


# --- Post-create hooks ---

async def _situation_post_create(socket, item):
    """Auto-set location for new situations from HexMap party_location."""
    game_id = socket.context.frame.get("game_id")
    if not game_id:
        return

    @sync_to_async(thread_sensitive=False)
    def _set_location():
        HexMap = apps.get_model('cards', 'HexMap')
        hm = HexMap.objects.filter(game_id=game_id).first()
        if hm and hm.party_location:
            item.location = hm.party_location
            item.save(update_fields=["location"])

    await _set_location()


async def _character_post_create(socket, item):
    """Auto-create default cards for new characters from their sheet."""
    if not hasattr(item, 'sheet_id') or not item.sheet_id:
        return

    @sync_to_async(thread_sensitive=False)
    def _create_default_cards():
        SheetDefaultCard = apps.get_model('cards', 'SheetDefaultCard')
        Card = apps.get_model('cards', 'Card')
        CharacterCard = apps.get_model('cards', 'CharacterCard')
        for dc in SheetDefaultCard.objects.filter(sheet_id=item.sheet_id):
            card = Card.objects.create(name=dc.name, notes=dc.notes)
            CharacterCard.objects.create(
                character=item, card=card, level=4, tag=dc.tag,
            )

    await _create_default_cards()


# --- Registration ---

def register_hooks():
    """Register cardplay hooks on all AliveMixin models."""
    from alive.mixin import AliveMixin
    from cards.cardplay_context import CardplayContext

    Situation = apps.get_model('cards', 'Situation')
    Character = apps.get_model('cards', 'Character')

    for model in apps.get_models():
        if not issubclass(model, AliveMixin):
            continue
        conf = model.get_alive_conf()
        conf.context_class = CardplayContext
        conf.event_handler = cardplay_event_handler
        conf.mount_hook = cardplay_mount_hook
        conf.params_hook = _make_params_hook(conf.template)
        conf.refresh_hook = _make_refresh_hook(conf.template)
        conf.info_hook = cardplay_info_hook
        conf.extra_subscriptions = cardplay_extra_subscriptions

        # Model-specific post-create hooks
        if model is Situation:
            conf.post_create_hook = _situation_post_create
        elif model is Character:
            conf.post_create_hook = _character_post_create
