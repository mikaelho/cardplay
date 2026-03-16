"""LiveView for the Sparks & Inspirations page (keeper-only)."""

import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pyview import LiveView, LiveViewSocket
from pyview.template import template_file, LiveRender
from pyview.meta import PyViewMeta

from .sparks import SPARKS
from .inspirations import INSPIRATIONS
from .knights import KNIGHTS, MYTHS, SEERS

TEMPLATE_PATH = str(Path(__file__).parent.parent / "templates" / "sparks.html")


def _roll_sparks():
    """Roll random values for all spark tables."""
    result = []
    for page_name, tables in SPARKS.items():
        page_tables = []
        for table_name, table in tables.items():
            col1_name, col2_name = table["columns"]
            i1 = random.randint(0, 11)
            i2 = random.randint(0, 11)
            page_tables.append({
                "name": table_name,
                "col1_name": col1_name,
                "col2_name": col2_name,
                "val1": table["col1"][i1],
                "val2": table["col2"][i2],
                "roll1": i1 + 1,
                "roll2": i2 + 1,
            })
        result.append({"name": page_name, "tables": page_tables})
    return result


def _roll_knights_myths():
    """Roll a random Knight and Myth (d6 + d12 each)."""
    d6_k = random.randint(1, 6)
    d12_k = random.randint(0, 11)
    d6_m = random.randint(1, 6)
    d12_m = random.randint(0, 11)
    d6_s = random.randint(1, 6)
    d12_s = random.randint(0, 11)
    return {
        "knight": KNIGHTS[d6_k][d12_k],
        "myth": MYTHS[d6_m][d12_m],
        "seer": SEERS[d6_s][d12_s],
    }


def _roll_inspirations():
    """Roll random values for all inspiration categories."""
    result = []
    for cat_name, values in INSPIRATIONS.items():
        idx = random.randint(0, len(values) - 1)
        result.append({
            "name": cat_name,
            "value": values[idx],
        })
    return result


@dataclass
class SparksContext:
    frame: dict = field(default_factory=dict)
    spark_pages: list = field(default_factory=list)
    knights_myths: dict = field(default_factory=dict)
    inspirations: list = field(default_factory=list)
    # Sidebar dice (needed by frame_bottom.html)
    quick_d6: int = 6
    quick_d6_svg: str = ""
    quick_d12: int = 12


def create_sparks_liveview():
    """Factory for the Sparks & Inspirations LiveView."""

    class SparksLiveView(LiveView[SparksContext]):

        async def render(self, context: SparksContext, meta: PyViewMeta):
            return LiveRender(template_file(TEMPLATE_PATH), context, meta)

        async def mount(self, socket: LiveViewSocket[SparksContext], session: dict[str, Any]):
            from alive import _frame_context_provider
            from cards.ui import render_die_svg

            frame_data = {}
            if _frame_context_provider:
                frame_data = await _frame_context_provider(session)

            socket.context = SparksContext(
                frame=frame_data,
                spark_pages=_roll_sparks(),
                knights_myths=_roll_knights_myths(),
                inspirations=_roll_inspirations(),
            )
            socket.context.quick_d6_svg = render_die_svg(socket.context.quick_d6, css_class="h-8 w-8")

        async def handle_event(self, event: str, payload: dict, socket: LiveViewSocket[SparksContext]):
            if event == "refresh":
                socket.context.spark_pages = _roll_sparks()
                socket.context.knights_myths = _roll_knights_myths()
                socket.context.inspirations = _roll_inspirations()
            elif event == "quick_roll_d6":
                socket.context.quick_d6 = random.randint(1, 6)
                from cards.ui import render_die_svg
                socket.context.quick_d6_svg = render_die_svg(socket.context.quick_d6, css_class="h-8 w-8")
            elif event == "quick_roll_d12":
                socket.context.quick_d12 = random.randint(1, 12)

    return SparksLiveView
