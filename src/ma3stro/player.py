"""Audio playback with sample-accurate position, pause/resume and seek.

Decoding is done once up front with pydub (which shells out to ffmpeg for
mp3/m4a), producing a float32 numpy buffer. Playback streams that buffer through
sounddevice, tracking the exact frame offset so the reported position reflects
what has actually been sent to the output device rather than wall-clock time.
"""

from __future__ import annotations

import threading
import warnings
from pathlib import Path

import numpy as np
import sounddevice as sd

with warnings.catch_warnings():
    # pydub emits SyntaxWarnings from its regexes and a RuntimeWarning when
    # ffmpeg isn't on PATH at import time; neither is actionable here.
    warnings.simplefilter("ignore")
    from pydub import AudioSegment


class Player:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        seg = AudioSegment.from_file(self.path)

        self.samplerate = seg.frame_rate
        self.channels = seg.channels

        # Interleaved samples -> (frames, channels) float32 in [-1, 1].
        samples = np.array(seg.get_array_of_samples())
        if self.channels > 1:
            samples = samples.reshape((-1, self.channels))
        else:
            samples = samples.reshape((-1, 1))
        max_val = float(1 << (8 * seg.sample_width - 1))
        self._buf = (samples.astype(np.float32) / max_val)

        self.total_frames = self._buf.shape[0]
        self.duration = self.total_frames / self.samplerate

        self._pos = 0  # next frame to play
        self._paused = False
        self._finished = False
        self._gain = 1.0  # linear playback gain in [0, 1]
        self._muted = False
        self._lock = threading.Lock()
        self._stream: sd.OutputStream | None = None

    # -- lifecycle ---------------------------------------------------------
    def start(self) -> None:
        self._stream = sd.OutputStream(
            samplerate=self.samplerate,
            channels=self.channels,
            dtype="float32",
            callback=self._callback,
        )
        self._stream.start()

    def close(self) -> None:
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None

    def _callback(self, outdata, frames, time_info, status):  # noqa: ARG002
        with self._lock:
            if self._paused or self._finished:
                outdata.fill(0)
                return
            start = self._pos
            end = min(start + frames, self.total_frames)
            n = end - start
            gain = 0.0 if self._muted else self._gain
            outdata[:n] = self._buf[start:end] * gain
            if n < frames:
                outdata[n:].fill(0)
                self._finished = True
            self._pos = end

    # -- transport ---------------------------------------------------------
    def toggle_pause(self) -> None:
        with self._lock:
            self._paused = not self._paused

    def seek(self, seconds: float) -> None:
        """Seek by a relative number of seconds (negative to rewind)."""
        with self._lock:
            target = self._pos + int(seconds * self.samplerate)
            self._pos = max(0, min(target, self.total_frames))
            if self._pos < self.total_frames:
                self._finished = False

    def seek_to(self, seconds: float) -> None:
        with self._lock:
            self._pos = max(0, min(int(seconds * self.samplerate), self.total_frames))
            if self._pos < self.total_frames:
                self._finished = False

    def adjust_volume(self, delta: float) -> None:
        """Change the playback gain by ``delta`` (clamped to [0, 1])."""
        with self._lock:
            self._gain = max(0.0, min(1.0, self._gain + delta))
            if self._gain > 0:
                self._muted = False

    def toggle_mute(self) -> None:
        with self._lock:
            self._muted = not self._muted

    # -- state -------------------------------------------------------------
    @property
    def position(self) -> float:
        with self._lock:
            return self._pos / self.samplerate

    @property
    def paused(self) -> bool:
        return self._paused

    @property
    def volume(self) -> float:
        """Effective gain, accounting for mute."""
        with self._lock:
            return 0.0 if self._muted else self._gain

    @property
    def muted(self) -> bool:
        return self._muted

    @property
    def finished(self) -> bool:
        return self._finished
