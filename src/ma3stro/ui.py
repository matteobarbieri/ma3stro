"""Terminal UI: a large auto-scaling ASCII clock plus a cue sidebar.

The clock is rendered from 5-row base glyphs that are scaled (independently in x
and y) to fill the available space, so the display grows with the terminal and
occupies the bulk of the screen.
"""

from __future__ import annotations

from rich.align import Align
from rich.console import Console, Group
from rich.layout import Layout
from rich.panel import Panel
from rich.progress_bar import ProgressBar
from rich.text import Text

from .cues import CueSheet

# 5-row base glyphs. "#" = lit cell, " " = blank.
_GLYPHS = {
    "0": ["###", "# #", "# #", "# #", "###"],
    "1": ["  #", "  #", "  #", "  #", "  #"],
    "2": ["###", "  #", "###", "#  ", "###"],
    "3": ["###", "  #", "###", "  #", "###"],
    "4": ["# #", "# #", "###", "  #", "  #"],
    "5": ["###", "#  ", "###", "  #", "###"],
    "6": ["###", "#  ", "###", "# #", "###"],
    "7": ["###", "  #", "  #", "  #", "  #"],
    "8": ["###", "# #", "###", "# #", "###"],
    "9": ["###", "# #", "###", "  #", "###"],
    ":": [" ", "#", " ", "#", " "],  # dots on rows 1 and 3
    " ": ["   ", "   ", "   ", "   ", "   "],
}

_BASE_H = 5
_GLYPH_GAP = 1  # base columns between glyphs


def fmt_time(seconds: float) -> str:
    seconds = max(0, int(seconds))
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


def _base_width(text: str) -> int:
    width = 0
    for i, ch in enumerate(text):
        width += len(_GLYPHS.get(ch, _GLYPHS[" "])[0])
        if i < len(text) - 1:
            width += _GLYPH_GAP
    return width


def render_big(text: str, max_w: int, max_h: int) -> Text:
    """Render ``text`` as scaled block glyphs that fit within max_w x max_h."""
    base_w = _base_width(text) or 1
    # Cells are taller than wide, so allow horizontal scale to run ahead of
    # vertical to keep digits looking roughly proportioned.
    sy = max(1, max_h // _BASE_H)
    sx = max(1, max_w // base_w)
    sx = min(sx, sy * 2 + 1)

    rows = ["" for _ in range(_BASE_H * sy)]
    for i, ch in enumerate(text):
        glyph = _GLYPHS.get(ch, _GLYPHS[" "])
        for r in range(_BASE_H):
            line = "".join(("█" if c == "#" else " ") * sx for c in glyph[r])
            for k in range(sy):
                rows[r * sy + k] += line
        if i < len(text) - 1:
            for r in range(len(rows)):
                rows[r] += " " * (_GLYPH_GAP * sx)

    out = Text()
    for j, row in enumerate(rows):
        out.append(row, style="bold cyan")
        if j < len(rows) - 1:
            out.append("\n")
    return out


def _sidebar(sheet: CueSheet, position: float, show_countdown: bool) -> Group:
    items: list = []
    current = sheet.current(position)
    upcoming = sheet.upcoming(position)

    items.append(Text("NOW", style="bold dim"))
    if current is not None:
        line = Text()
        line.append("▸ ", style="bold green")
        line.append(current.label, style="bold green")
        if current.art:
            line.append("  " + current.art)
        items.append(line)
    else:
        items.append(Text("—", style="dim"))

    items.append(Text(""))
    items.append(Text("NEXT", style="bold dim"))
    if upcoming:
        nxt = upcoming[0]
        line = Text()
        line.append("▸ ", style="bold yellow")
        line.append(nxt.label, style="bold yellow")
        if show_countdown and sheet.show_countdown:
            remaining = max(0, nxt.time - position)
            line.append(f"  in {int(remaining)}s", style="yellow")
        if nxt.art:
            line.append("  " + nxt.art)
        items.append(line)
        for cue in upcoming[1:6]:
            sub = Text()
            sub.append("· ", style="dim")
            sub.append(cue.label, style="dim")
            if cue.art:
                sub.append("  " + cue.art, style="dim")
            items.append(sub)
    else:
        items.append(Text("—", style="dim"))

    return Group(*items)


class Renderer:
    def __init__(self, console: Console, sheet: CueSheet, show_countdown: bool, title: str):
        self.console = console
        self.sheet = sheet
        self.show_countdown = show_countdown
        self.title = title
        self.has_cues = bool(sheet.cues)

    def render(self, position: float, duration: float, paused: bool) -> Layout:
        w, h = self.console.size
        root = Layout()
        root.split_column(
            Layout(name="body"),
            Layout(name="footer", size=3),
        )

        sidebar_w = max(24, w // 4) if self.has_cues else 0
        clock_w = w - sidebar_w - 6  # account for panel borders/padding
        clock_h = int((h - 3) * 0.85)

        clock = render_big(fmt_time(position), clock_w, clock_h)
        sub = Text(f"{fmt_time(position)} / {fmt_time(duration)}", style="dim", justify="center")
        clock_group = Align.center(Group(Align.center(clock), Text(""), sub), vertical="middle")
        clock_panel = Panel(clock_group, title=self.title, border_style="cyan")

        if self.has_cues:
            body = Layout()
            body.split_row(
                Layout(clock_panel, name="clock"),
                Layout(
                    Panel(_sidebar(self.sheet, position, self.show_countdown),
                          title="CUES", border_style="magenta"),
                    name="cues",
                    size=sidebar_w,
                ),
            )
            root["body"].update(body)
        else:
            root["body"].update(clock_panel)

        # footer: progress bar + controls
        bar = ProgressBar(total=max(duration, 0.001), completed=position, width=None)
        status = "⏸ PAUSED" if paused else "▶ PLAYING"
        controls = Text.assemble(
            (f"{status}   ", "bold green" if not paused else "bold yellow"),
            ("[space]", "bold"), " play/pause   ",
            ("[←/→]", "bold"), " seek 5s   ",
            ("[q]", "bold"), " quit",
            style="dim",
        )
        footer = Group(bar, controls)
        root["footer"].update(Panel(footer, border_style="dim"))
        return root
