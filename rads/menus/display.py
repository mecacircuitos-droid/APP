from __future__ import annotations

from typing import List, Tuple

from rads.core import Key, LCD, RADSState, Screen
from rads.ui.lcd_helpers import header_scientific_atlanta


def _fmt(x, nd: int = 3) -> str:
    if isinstance(x, (int, float)):
        return f"{x:.{nd}f}"
    return str(x)


def register_display(sim: RADSState) -> None:
    sim.screens["display"] = Screen(
        id="display",
        title="DISPLAY",
        help_text="View last results",
        render=_render_main,
        handle=_handle_main,
    )

    sim.screens["display_summary"] = Screen(
        id="display_summary",
        title="DISPLAY / SUMMARY",
        help_text="Session summary",
        render=_render_summary,
        handle=_handle_summary,
    )

    sim.screens["display_track"] = Screen(
        id="display_track",
        title="DISPLAY / TRACK",
        help_text="Track view",
        render=_render_track,
        handle=_handle_track,
    )

    sim.screens["display_vib"] = Screen(
        id="display_vib",
        title="DISPLAY / VIBRATION",
        help_text="Vibration view",
        render=_render_vib,
        handle=_handle_vib,
    )


def _render_main(sim: RADSState) -> LCD:
    lines = header_scientific_atlanta(sim, "DISPLAY")
    items = ["Summary", "Track", "Vibration"]
    idx = sim.menu_index % len(items)
    lines.append("")
    for i, it in enumerate(items):
        prefix = ">" if i == idx else " "
        lines.append(f"{prefix} {it}"[:38])
    lines += ["", _context_line(sim), ""]
    return LCD(lines=lines, highlight_line=4 + idx, footer="UP/DN  DO  QUIT".ljust(38))


def _handle_main(sim: RADSState, key: Key) -> None:
    items = ["display_summary", "display_track", "display_vib"]

    # global keys
    if key == Key.F1:
        sim.push("measure"); sim.menu_index = 0; return
    if key == Key.F3:
        sim.push("diags"); sim.menu_index = 0; return
    if key == Key.F4:
        sim.push("manager"); sim.menu_index = 0; return

    if key in (Key.UP, Key.DOWN):
        sim.menu_index = (sim.menu_index + (1 if key == Key.DOWN else -1)) % len(items)
        return

    if key == Key.DO:
        sim.push(items[sim.menu_index % len(items)])
        sim.menu_index = 0
        return

    if key == Key.QUIT:
        sim.pop(); sim.menu_index = 0
        return


def _render_summary(sim: RADSState) -> LCD:
    lines = header_scientific_atlanta(sim, "Summary")
    flights = sorted(sim.measurements.keys())
    lines.append("")
    if not flights:
        lines += ["No results yet.", "Run MEASURE first.", "", _context_line(sim)]
        return LCD(lines=lines, highlight_line=None, footer="QUIT".ljust(38))

    idx = sim.menu_index % len(flights)
    lines.append("Flights:")
    for i, fid in enumerate(flights[:5]):
        prefix = ">" if i == idx else " "
        count = len(sim.measurements.get(fid, {}))
        lines.append(f"{prefix} {fid}  ({count} runs)"[:38])
    while len(lines) < 9:
        lines.append("")
    return LCD(lines=lines, highlight_line=5 + idx, footer="DO set active  QUIT".ljust(38))


def _handle_summary(sim: RADSState, key: Key) -> None:
    flights = sorted(sim.measurements.keys())
    if not flights:
        if key == Key.QUIT:
            sim.pop()
        return

    if key in (Key.UP, Key.DOWN):
        sim.menu_index = (sim.menu_index + (1 if key == Key.DOWN else -1)) % len(flights)
        return

    if key == Key.DO:
        sim.flight_id = flights[sim.menu_index % len(flights)]
        sim.last_message = f"Active Flight: {sim.flight_id}"
        sim.menu_index = 0
        sim.pop()
        return

    if key == Key.QUIT:
        sim.menu_index = 0
        sim.pop()
        return


def _render_track(sim: RADSState) -> LCD:
    lines = header_scientific_atlanta(sim, "Track")
    fid, last_state, last = _get_last(sim)
    lines.append("")
    if not last:
        lines += ["No track data.", "Run MEASURE first.", "", _context_line(sim)]
        return LCD(lines=lines, highlight_line=None, footer="QUIT".ljust(38))

    t = last.get("track_rel_mm", {})
    lines.append(f"Flight {fid}  {last_state}"[:38])
    lines.append(f"BLU {t.get('BLU','-'):>4} mm   RED {t.get('RED','-'):>4} mm"[:38])
    lines.append(f"ORG {t.get('ORG','-'):>4} mm   GRN {t.get('GRN','-'):>4} mm"[:38])
    lines += ["", "(values rel. mean)", ""]
    return LCD(lines=lines, highlight_line=None, footer="QUIT".ljust(38))


def _handle_track(sim: RADSState, key: Key) -> None:
    if key == Key.QUIT:
        sim.pop()


def _render_vib(sim: RADSState) -> LCD:
    lines = header_scientific_atlanta(sim, "Vibration")
    fid, last_state, last = _get_last(sim)
    lines.append("")
    if not last:
        lines += ["No vibration data.", "Run MEASURE first.", "", _context_line(sim)]
        return LCD(lines=lines, highlight_line=None, footer="QUIT".ljust(38))

    lat = last.get("lat_1r_ips", last.get("vib_1r_ips", "-"))
    latp = last.get("lat_1r_phase_deg", last.get("vib_1r_phase_deg", "-"))
    ver = last.get("vert_1r_ips", "-")
    verp = last.get("vert_1r_phase_deg", "-")
    v4 = last.get("vib_4r_ips", "-")
    p4 = last.get("vib_4r_phase_deg", "-")

    lines.append(f"Flight {fid}  {last_state}"[:38])
    lines.append(f"LAT1R: {_fmt(lat)} ips @ {_fmt(latp,1)}°"[:38])
    lines.append(f"VRT1R: {_fmt(ver)} ips @ {_fmt(verp,1)}°"[:38])
    lines.append(f"4R   : {_fmt(v4)} ips @ {_fmt(p4,1)}°"[:38])
    lines += ["", "(simulated numbers)", ""]
    return LCD(lines=lines, highlight_line=None, footer="QUIT".ljust(38))


def _handle_vib(sim: RADSState, key: Key) -> None:
    if key == Key.QUIT:
        sim.pop()


def _context_line(sim: RADSState) -> str:
    tail = sim.tail_number or "-"
    plan = sim.flight_plan or "-"
    fid = sim.flight_id or "-"
    return f"Tail:{tail}  Plan:{plan}  F:{fid}"[:38]


def _get_last(sim: RADSState) -> Tuple[str, str, dict]:
    # pick active flight if available; otherwise last created
    fid = sim.flight_id if sim.flight_id in sim.measurements else (sorted(sim.measurements.keys())[-1] if sim.measurements else "")
    if not fid:
        return "", "", {}
    runs = sim.measurements.get(fid, {})
    if not runs:
        return fid, "", {}
    # pick the last inserted (dict preserves insertion order)
    last_state = list(runs.keys())[-1]
    return fid, last_state, runs[last_state]
