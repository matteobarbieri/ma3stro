"""Command-line entry point: wire player, cues, key reader and UI together."""

from __future__ import annotations

import argparse
import shutil
import sys
import time
from pathlib import Path

from rich.console import Console
from rich.live import Live

from . import __version__
from .cues import load_for_track
from .keys import KeyReader
from .player import Player
from .ui import Renderer

SEEK_SECONDS = 5.0
VOLUME_STEP = 0.05
REFRESH_HZ = 15


def _volume_arg(value: str) -> int:
    try:
        v = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"volume must be an integer, got {value!r}")
    if not 0 <= v <= 100:
        raise argparse.ArgumentTypeError(f"volume must be between 0 and 100, got {v}")
    return v


def _check_ffmpeg(track: Path) -> None:
    if track.suffix.lower() == ".wav":
        return
    if shutil.which("ffmpeg") is None:
        sys.exit(
            "Error: ffmpeg not found on PATH. It is required to decode "
            f"'{track.suffix}' files. Install it (e.g. `brew install ffmpeg`) "
            "or use a .wav file."
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="ma3stro",
        description="Play a backing track with a large ASCII clock and side cues.",
    )
    parser.add_argument("track", help="audio file to play (wav, mp3, m4a, ...)")
    parser.add_argument("--cues", help="cue sidecar YAML (default: <track>.cues.yaml)")
    parser.add_argument(
        "--no-countdown",
        action="store_true",
        help="hide the 'next section in Ns' countdown",
    )
    parser.add_argument(
        "--start", metavar="SECONDS", type=float, default=0.0,
        help="start playback at this offset (seconds)",
    )
    parser.add_argument(
        "--volume", metavar="LEVEL", type=_volume_arg, default=50,
        help="initial volume level (0-100, default: 50)",
    )
    parser.add_argument("--version", action="version", version=f"ma3stro {__version__}")
    args = parser.parse_args(argv)

    track = Path(args.track)
    if not track.exists():
        sys.exit(f"Error: track not found: {track}")
    _check_ffmpeg(track)

    sheet = load_for_track(track, args.cues)
    show_countdown = not args.no_countdown

    console = Console()
    try:
        player = Player(track)
    except Exception as exc:  # decoding failure
        sys.exit(f"Error: could not load audio: {exc}")

    if args.start:
        player.seek_to(args.start)

    player.set_volume(args.volume / 100.0)

    renderer = Renderer(console, sheet, show_countdown, title=track.name)

    quit_flag = {"q": False}

    def on_key(key: str) -> None:
        if key == "q":
            quit_flag["q"] = True
        elif key == "space":
            player.toggle_pause()
        elif key == "left":
            player.seek(-SEEK_SECONDS)
        elif key == "right":
            player.seek(SEEK_SECONDS)
        elif key == "up":
            player.adjust_volume(VOLUME_STEP)
        elif key == "down":
            player.adjust_volume(-VOLUME_STEP)
        elif key == "m":
            player.toggle_mute()

    keys = KeyReader(on_key)
    keys.start()
    player.start()

    try:
        with Live(
            renderer.render(
                player.position, player.duration, player.paused, player.volume
            ),
            console=console,
            screen=True,
            refresh_per_second=REFRESH_HZ,
            transient=True,
        ) as live:
            while not quit_flag["q"] and not player.finished:
                live.update(
                    renderer.render(
                        player.position, player.duration, player.paused, player.volume
                    )
                )
                time.sleep(1 / REFRESH_HZ)
    except KeyboardInterrupt:
        pass
    finally:
        keys.stop()
        player.close()

    console.print(f"Done — {track.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
