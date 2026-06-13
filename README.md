# ma3stro

A command-line backing-track player that shows a **large ASCII clock** and a
**cue sidebar** so you can see what part of the song is coming up.

```
┌──────────────────────────────────┬────────────────┐
│                                   │ NOW            │
│   ████   ██    ████   ████        │ ▸ Chorus  🎸    │
│   █  █  ███      █    █  █         │                │
│   █  █    █    ███      █          │ NEXT           │
│   █  █    █    █      █  █         │ ▸ Bridge in 8s │
│   ████   ███   ████   ████        │ · Solo  🔥      │
│            01:23                  │ · Outro        │
├───────────────────────────────────┴────────────────┤
│ ████████████░░░░░░░  ▶ PLAYING  [space] [←/→] [q]   │
└─────────────────────────────────────────────────────┘
```

## Install

Requires **[uv](https://docs.astral.sh/uv/)** to manage the environment and run
the tool:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh   # or: brew install uv
```

Also requires **ffmpeg** for mp3/m4a decoding (wav works without it):

```bash
brew install ffmpeg          # macOS
```

Then, from the repo:

```bash
uv sync
```

## Usage

```bash
uv run ma3stro path/to/backing.m4a
```

Supported formats: `wav`, `mp3`, `m4a`, and anything else ffmpeg can decode.

### Cues

Create a sidecar YAML next to your track named `<track>.cues.yaml`
(e.g. `backing.m4a` → `backing.cues.yaml`). It loads automatically; otherwise
pass `--cues path.yaml`. See [`examples/demo.cues.yaml`](examples/demo.cues.yaml).

```yaml
show_countdown: true
cues:
  - { time: "0:00", label: "Intro",  art: "🎵" }
  - { time: "1:04", label: "Chorus", art: "🎸" }
  - { time: "2:30", label: "Bridge" }
```

- `time` accepts `m:ss`, `mm:ss`, `h:mm:ss`, or a raw number of seconds.
- A cue is the active section from its `time` until the next cue.
- `art` is an optional symbol / short note shown beside the label.

### Options

| Flag | Description |
| --- | --- |
| `--cues PATH` | Use a specific cue file instead of the auto-detected sidecar. |
| `--no-countdown` | Hide the "next section in Ns" countdown. |
| `--start SECONDS` | Begin playback at an offset. |

### Controls

| Key | Action |
| --- | --- |
| `space` | Play / pause |
| `←` / `→` | Seek ∓5 seconds |
| `↑` / `↓` | Volume ±5% |
| `m` | Mute / unmute |
| `q` | Quit |

## Web version

`web/index.html` is a self-contained, browser-based port with the same
look — big block-glyph clock, cue sidebar, progress footer — and the same
keyboard controls. It plays through the native `<audio>` element, so there
are no Python dependencies and nothing to decode up front.

Open it directly, or serve the folder:

```bash
open web/index.html              # macOS — just double-click works too
# or, if your browser blocks file:// drops:
uv run python -m http.server -d web 8000   # then visit localhost:8000
```

Drop a backing track (or click **Choose track**); optionally add a cue
sheet with **Add cues** (the same `.cues.yaml` format, or `.json` with the
same shape). Supported audio is whatever the browser can play
(`wav`, `mp3`, `m4a`, `ogg`, `flac`, …).

As a section approaches, a large countdown appears below the clock in the
final few seconds (8 by default).

You can pre-set options via the URL query string:
`index.html?volume=70&start=30&lead=8` — volume 0–100, start in seconds, and
`lead` seconds for the approaching-section countdown.
