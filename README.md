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
| `q` | Quit |
