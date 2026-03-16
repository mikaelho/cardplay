# Separation Plan: Cardplay-Specific Code from the Alive Framework

## Problem

~56% of alive's code is cardplay-specific. Alive (in `../alive`) is meant to be a generic LiveView-style CRUD framework for Django, but it currently contains hex maps, dice rolling, hand/keeper/situation logic, and other RPG game features.

## Audit Results

| File | Total Lines | App-Specific | % |
|---|---|---|---|
| `views.py` | 4021 | ~2400 | ~60% |
| `ui.py` | 1186 | ~1100 | ~93% |
| Templates | ~1900 | ~1200 | ~63% |
| Static JS | 498 | 214 | ~43% |
| conf.py, mixin.py, store.py | ~1100 | 0 | 0% |
| **Total** | **~8700** | **~4900** | **~56%** |

### views.py Detail

**Cardplay-specific `ModelContext` fields:**
- `hand_*` (lines 127-134): hand_is_player, hand_character_id, hand_card_count, hand_drawn, hand_cards, hand_can_draw, hand_collapsed, hand_active_situation_id
- `situation_*` (lines 136-153): situation_cards, past_situations, active_situation_name/notes, situation_dice/assignments/dice_assigned/resolved/all_assigned, situation_card_editing_*
- `is_keeper`, `keeper_*` (lines 149-155)
- `hex_*` / `hex_map_*` (lines 157-198): all hex map state, rivers, overlays, notes, party location, timeline
- `quick_d6`, `quick_d6_svg`, `quick_d12` (lines 184-185)
- `map_detail*`, `map_create_*`, `map_situation_active`, `copy_map_*` (lines 176-198)
- `time_advance_*`, `current_game_time` (lines 200-205)
- `site_map_*` (lines 206-221)
- `search_*` (lines 223-226)
- `has_sheet_defaults` (line 119)

**Cardplay-specific event handlers:**
- Keeper card creation in `save_create` (lines 580-647)
- Auto-location and default card creation on create (lines 672-705)
- `sync_sheet_cards` (lines 730-758)
- Hand events: `toggle_hand_collapsed`, `draw_hand`, `toggle_hand_situation` (lines 1436-1506)
- Situation card events: `remove_situation_card`, `adjust_situation_card_level`, situation card editing (lines 1508-1604)
- Keeper events: `rename_situation`, `keeper_start_add/cancel/create`, `keeper_add_card` (lines 1607-1672)
- Map editing events: ~400 lines (lines 1674-2079)
- Map create dialog (lines 2081-2157)
- Time advance events (lines 2159-2281)
- Copy map, cancel_map_situation (lines 2283-2384)
- Map detail popup events (lines 2386-2488)
- River drawing, terrain/overlay painting (lines 2490-2651)
- Situation dice events: roll, assign, unassign, lock, toggle_used, resolve (lines 2653-2822)
- Search modal events (lines 2824-2982)
- Quick dice roll events (lines 2984-2996)

**Cardplay-specific private methods:**
- `_load_situation_data` (lines 3067-3271)
- `_commit_river` (lines 3272-3294)
- `_close_map_detail`, `_refresh_map_detail` (lines 3296-3371)
- `_load_map_data` (lines 3373-3504)
- `_save_site_map_data` (lines 3506-3533)
- `_handle_site_map_edit_click`, `_handle_site_map_view_click` (lines 3535-3714)
- `_load_hand_data` (lines 3716-3823)

### Templates

**Generic (stay in alive):** `items.html`, `grid.html`, `index.html`, `create_form.html`, `frame_top.html` (mostly), `frame_bottom.html` (mostly)

**Cardplay-specific (move to cardplay):** `map.html` (641 lines), `hand_footer.html` (118 lines), `situation.html` (124 lines), `situation_cards.html` (300 lines), `search.html` (44 lines)

### ui.py

**Generic:** `render_theme_picker`, `render_theme_script` (lines 1-78)

**Cardplay-specific:** `render_die_svg`/`DIE_CSS` (lines 81-117), `render_rating` (lines 120-171), all hex map functions (lines 174-898), all site map functions (lines 980-1186)

### Static Files

**Cardplay-specific:** `hexmap.js` (214 lines). `keyboard.js` has minor cardplay-aware selectors to clean up.

---

## Proposed Architecture

### Hook-Based Extension System

Add to `AliveConf`:
```python
event_handler: Callable | None = None        # async (event, payload, socket) -> bool
mount_hook: Callable | None = None           # async (socket, session) -> None
params_hook: Callable | None = None          # async (socket, url, params) -> None
refresh_hook: Callable | None = None         # async (socket) -> None
info_hook: Callable | None = None            # async (event, socket) -> None
disconnect_hook: Callable | None = None      # async (socket) -> None
extra_subscriptions: Callable | None = None  # async (socket) -> list[str]
```

### Custom Context

Add `extra: dict` field to `ModelContext`. Framework merges `extra` into the template context so templates access `{{hand_cards}}` not `{{extra.hand_cards}}`.

### Custom Templates

- `setup_alive()` accepts `template_dirs` for app template paths
- `frame_top.html` and `frame_bottom.html` become overridable by the app
- Cardplay templates move to cardplay's own template directory

---

## Implementation Phases

### Phase 1: Add Hook Infrastructure (No Behavioral Changes)

1. Add hook fields to `AliveConf` with `None` defaults
2. Add `extra: dict` to `ModelContext` and `IndexContext`
3. Wire hook calls into `GeneratedModelLiveView`:
   - `mount`: call `mount_hook` if set
   - `handle_params`: call `params_hook` if set
   - `handle_event`: call `event_handler` first; if returns `True`, skip built-in handling
   - `_refresh_view_async`: call `refresh_hook` if set
   - `handle_info`: call `info_hook` if set
   - `disconnect`: call `disconnect_hook` if set
4. Add `template_dirs` parameter to `setup_alive()`
5. Make frame templates overridable

### Phase 2: Move Cardplay Logic to Hooks

1. Create `cards/alive_hooks.py` with:
   - `cardplay_mount_hook` — sets hand/keeper/dice state in `extra`
   - `cardplay_params_hook` — calls situation/map data loaders
   - `cardplay_event_handler` — handles all cardplay events
   - `cardplay_refresh_hook` — refreshes situation/map/hand data
   - `cardplay_info_hook` — handles Card channel refresh
2. Move all private methods (`_load_situation_data`, `_load_map_data`, `_load_hand_data`, `_commit_river`, map detail, site map handlers) to cardplay
3. Register hooks on appropriate `AliveConf` instances (Situation, HexMap, Character, etc.)

### Phase 3: Move Templates

1. Move `map.html`, `situation.html`, `situation_cards.html`, `hand_footer.html`, `search.html` to cardplay's template directory
2. Create cardplay overrides of `frame_top.html` (player/game selectors) and `frame_bottom.html` (dice, search, hand footer)
3. Clean alive's frame templates to be generic

### Phase 4: Move UI Rendering

1. Move `render_die_svg`, `render_rating`, all hex map functions, all site map functions from alive `ui.py` to `cards/ui.py`
2. Move `hexmap.js` from alive static to cardplay static
3. Clean `keyboard.js` of cardplay-specific selectors

### Phase 5: Strip ModelContext

1. Remove all cardplay fields from `ModelContext` (hand_*, situation_*, hex_*, keeper_*, map_*, time_advance_*, quick_d6/d12, search_*, site_map_*, has_sheet_defaults)
2. Remove cardplay fields from `IndexContext`

### Phase 6: Clean Framework Code

1. Remove cardplay branches from `save_create` (keeper card creation, auto-location, default cards)
2. Remove cardplay code from `mount` (hand detection, die SVG, Card channel subscription)
3. Remove `_load_situation_data`/`_load_map_data` calls from `handle_params` and `_refresh_view_async`
4. Remove Card channel handling from `handle_info`

### Phase 7: Add Guidance Documentation

1. Add/update README in `../alive/` explaining that alive is a generic framework and must not contain app-specific code; document the hook system for extending it
2. Add/update README in cardplay explaining the separation boundary and that cardplay-specific features belong in `cards/alive_hooks.py` and cardplay templates, not in alive

---

## Risks and Cautions

1. **Template variable access.** If `extra` dict is not merged into the template namespace, all templates need `{{extra.hand_cards}}` instead of `{{hand_cards}}`. Strongly prefer merging `extra` into the context.

2. **Template name checks.** Lines like `conf.template == "situation.html"` in views.py decide whether to load situation data. Replace with the hook system — the app's `params_hook`/`refresh_hook` handles this.

3. **Cross-view subscriptions.** The hand footer subscribes to the Card channel even on non-card pages. The `extra_subscriptions` hook must support this.

4. **Closure references.** Cardplay hooks need access to `store`, `conf`, `model` from the `create_model_liveview` closure. Pass them as arguments or make them accessible via socket metadata.

5. **Incremental migration.** Each phase must produce a working system. Phase 1 adds infrastructure. Phase 2 duplicates logic into hooks (old code still present). Phases 3-6 remove old code. Test at each stage.

6. **`items.html` "Sync Sheet Cards" button.** Gated by `has_sheet_defaults`. Move to app level — the refresh hook sets `extra["has_sheet_defaults"]` and the app's template override checks it.

7. **Sidebar dice.** Currently rendered for all models. Either make opt-in via a framework flag, or move entirely to cardplay's frame override.
