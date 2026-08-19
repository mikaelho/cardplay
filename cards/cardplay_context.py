"""Cardplay-specific context extending alive's ModelContext."""

from dataclasses import dataclass, field

from alive.views import ModelContext


@dataclass
class CardplayContext(ModelContext):
    """ModelContext with cardplay-specific fields."""

    # Hand footer
    hand_is_player: bool = False
    hand_character_id: int | None = None
    hand_card_count: int = 0
    hand_cards: list[dict] = field(default_factory=list)
    situation_card_pks: set = field(default_factory=set)
    hand_collapsed: bool = False
    hand_active_situation_id: int | None = None
    # Situation
    situation_cards: list[dict] = field(default_factory=list)
    past_situations: list[dict] = field(default_factory=list)
    active_situation_name: str = ""
    active_situation_notes: str = ""
    situation_dice: list[int] = field(default_factory=list)
    situation_assignments: dict = field(default_factory=dict)
    situation_dice_assigned: bool = False
    situation_resolved: bool = False
    situation_all_assigned: bool = False
    situation_selected_die: str = ""
    situation_card_editing_id: str = ""
    situation_card_editing_field: str = ""
    situation_card_editing_value: str = ""
    # Keeper
    is_keeper: bool = False
    keeper_character_id: int | None = None
    keeper_available_cards: list[dict] = field(default_factory=list)
    keeper_player_card_groups: list[dict] = field(default_factory=list)
    keeper_adding: bool = False
    keeper_creating: bool = False
    # Hex map
    hex_map_svg: str = ""
    hex_map_edit: bool = False
    hex_map_palette: str = ""
    hex_overlay_palette: str = ""
    hex_active_symbol: str = ""
    hex_active_overlay: str = ""
    hex_overlay_mode: bool = False
    hex_show_overlays: bool = False
    hex_map_id: int | None = None
    hex_river_drawing: bool = False
    hex_current_river: list[str] = field(default_factory=list)
    hex_notes_mode: bool = False
    hex_selected_hex: str = ""
    hex_action_hex: str = ""
    hex_action_is_adjacent: bool = False
    hex_action_has_overlay: bool = False
    hex_action_overlay_revealed: bool = False
    hex_selected_note: str = ""
    hex_note_html: str = ""
    hex_note_editing: bool = False
    # Timeline / party location
    timeline_entries: list[dict] = field(default_factory=list)
    party_location: str = ""
    # Map create dialog
    map_create_open: bool = False
    map_create_type: str = ""
    map_create_name: str = ""
    map_create_notes: str = ""
    map_create_error: str = ""
    # Dice (sidebar)
    quick_d6: int = 6
    quick_d6_svg: str = ""
    quick_d12: int = 12
    # Map detail popup
    map_detail: dict = field(default_factory=dict)
    map_detail_editing: str = ""
    map_detail_draft: str = ""
    map_situation_active: bool = False
    # Copy map
    copy_map_open: bool = False
    copy_map_games: list[dict] = field(default_factory=list)
    copy_map_target: str = ""
    copy_map_error: str = ""
    # Time advance
    time_advance_open: bool = False
    time_advance_age: str = ""
    time_advance_year: str = ""
    time_advance_season: str = ""
    time_advance_day: str = ""
    time_advance_shift: str = ""
    current_game_time: str = ""
    # Site map
    site_map_open: bool = False
    site_map_hex: str = ""
    site_map_data: dict = field(default_factory=dict)
    site_map_svg: str = ""
    site_map_edit: bool = False
    site_map_tool: str = ""
    site_map_route_from: int = -1
    site_map_selected_type: str = ""
    site_map_selected_id: str = ""
    site_map_detail_name: str = ""
    site_map_detail_notes: str = ""
    site_map_detail_editing: str = ""
    site_map_detail_draft: str = ""
    # Search
    search_open: bool = False
    search_query: str = ""
    search_results: list[dict] = field(default_factory=list)
    # Model-specific flags
    has_sheet_defaults: bool = False
