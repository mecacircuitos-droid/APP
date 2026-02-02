from __future__ import annotations

from typing import List, Tuple

from rads.core import Key, LCD, RADSState, Screen
from rads.models.diagnosis import step_detail_for_bht412, step_summaries_for_bht412
from rads.ui.lcd_helpers import header_scientific_atlanta, softkey_bar_html


def register_diags(sim: RADSState) -> None:
    sim.screens["diags"] = Screen(
        id="diags",
        title="DIAGS",
        help_text="Sequential DIAGS (BHT-412-MM)",
        render=_render_main,
        handle=_handle_main,
    )

    sim.screens["diags_view"] = Screen(
        id="diags_view",
        title="DIAGS / VIEW",
        help_text="Step detail",
        render=_render_view,
        handle=_handle_view,
    )


def _active_runs(sim: RADSState) -> Tuple[str, dict]:
    if sim.flight_id and sim.flight_id in sim.measurements:
        return sim.flight_id, sim.measurements.get(sim.flight_id, {})
    if sim.measurements:
        fid = sorted(sim.measurements.keys())[-1]
        return fid, sim.measurements.get(fid, {})
    return "", {}


def _tag(status: str) -> str:
    return {
        "DONE": "DONE",
        "NEEDS": "NEED",
        "LOCKED": "LOCK",
        "MISSING": "MISS",
    }.get(status, status[:4].upper())


def _render_main(sim: RADSState) -> LCD:
    fid, runs = _active_runs(sim)

    lines = header_scientific_atlanta(sim, "DIAGS")

    if not (sim.aircraft_type or "").startswith("412"):
        lines.append("BHT-412-MM only"[:38].ljust(38))
        lines.append("Select Bell 412 in MEASURE"[:38].ljust(38))
        while len(lines) < 9:
            lines.append("".ljust(38))
        return LCD(lines=lines[:9], highlight_line=None, inv_lines=[8], footer_html=softkey_bar_html(sim))

    steps = step_summaries_for_bht412(runs)
    idx = sim.menu_index % max(1, len(steps))

    ftxt = fid if fid else "(no flight)"
    lines.append(f"BHT-412-MM  FLT {ftxt}"[:38].ljust(38))

    for i, s in enumerate(steps):
        tag = _tag(s.status)
        # keep short and aligned (38 cols)
        label = s.label[:28]
        line = f"{i+1}. {label:<28}{tag:>6}"[:38]
        lines.append(line.ljust(38))

    # 3 header + 1 context + 5 steps = 9 lines
    return LCD(lines=lines[:9], highlight_line=4 + idx, footer_html=softkey_bar_html(sim))


def _handle_main(sim: RADSState, key: Key) -> None:
    # global tabs
    if key == Key.F1:
        sim.push("measure"); sim.menu_index = 0; return
    if key == Key.F2:
        sim.push("display"); sim.menu_index = 0; return
    if key == Key.F4:
        sim.push("manager"); sim.menu_index = 0; return

    fid, runs = _active_runs(sim)
    steps = step_summaries_for_bht412(runs) if (sim.aircraft_type or "").startswith("412") else []
    if not steps:
        if key == Key.QUIT:
            sim.pop(); sim.menu_index = 0
        return

    if key in (Key.UP, Key.DOWN):
        sim.menu_index = (sim.menu_index + (1 if key == Key.DOWN else -1)) % len(steps)
        return

    if key == Key.DO:
        step = steps[sim.menu_index % len(steps)]
        title, lines = step_detail_for_bht412(runs, step.step_id, option_120k=1)
        sim.diag_title = title
        sim.diag_lines = lines
        sim.menu_index = 0
        sim.push("diags_view")
        sim.last_message = f"DIAGS: {step.step_id} ({step.status})"
        return

    if key == Key.QUIT:
        sim.pop(); sim.menu_index = 0
        return


def _render_view(sim: RADSState) -> LCD:
    title = sim.diag_title or "DIAGS"
    lines = header_scientific_atlanta(sim, title[:26])

    body = sim.diag_lines or ["No data"]
    view_rows = 5
    max_start = max(0, len(body) - view_rows)
    start = min(max(0, sim.menu_index), max_start)

    # line 4 (context)
    lines.append(f"Line {start+1}/{len(body)}"[:38].ljust(38))
    for ln in body[start:start + view_rows]:
        lines.append(str(ln)[:38].ljust(38))

    lines.append("UP/DN Scroll"[:38].ljust(38))
    lines.append("QUIT Back"[:38].ljust(38))

    return LCD(lines=lines[:9], highlight_line=None, inv_lines=[7, 8], footer_html=softkey_bar_html(sim))


def _handle_view(sim: RADSState, key: Key) -> None:
    # global tabs
    if key == Key.F1:
        sim.push("measure"); sim.menu_index = 0; return
    if key == Key.F2:
        sim.push("display"); sim.menu_index = 0; return
    if key == Key.F4:
        sim.push("manager"); sim.menu_index = 0; return

    body = sim.diag_lines or []
    view_rows = 5
    max_start = max(0, len(body) - view_rows)

    if key in (Key.UP, Key.DOWN):
        delta = 1 if key == Key.DOWN else -1
        sim.menu_index = min(max(0, sim.menu_index + delta), max_start)
        return

    if key == Key.QUIT:
        sim.menu_index = 0
        sim.pop()
        return
