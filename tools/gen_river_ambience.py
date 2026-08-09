#!/usr/bin/env python
"""Synthesize a seamless 12s forest-stream ambience loop (CC0 procedural).

Layers:
  - brown noise band 120-1800 Hz  -> river body/wash
  - white noise band 2500-6500 Hz -> water spray hiss
  - lowpassed wind with slow LFO  -> breeze through leaves
Crossfades the loop edges so the WAV loops cleanly in Godot.

Usage: python tools/gen_river_ambience.py
Output: assets/sfx/river_ambience.wav (mono 44.1k 16-bit)
"""

import wave
from pathlib import Path

import numpy as np
from numpy.fft import irfft, rfft, rfftfreq

SR = 44100
DUR = 12.0
OUT = Path(__file__).resolve().parents[1] / "assets" / "sfx" / "river_ambience.wav"


def band_filter(x: np.ndarray, lo: float, hi: float, rolloff: float = 0.1) -> np.ndarray:
    n = len(x)
    spec = rfft(x)
    freqs = rfftfreq(n, 1.0 / SR)
    mask = np.ones_like(spec)
    mask[freqs < lo] = np.clip((freqs[freqs < lo] / lo) ** rolloff, 0.0, 1.0) * 0.05
    mask[freqs > hi] = np.clip((hi / freqs[freqs > hi]) ** rolloff, 0.0, 1.0) * 0.05
    return irfft(spec * mask, n)


def seamless(x: np.ndarray, overlap_s: float = 1.0) -> np.ndarray:
    """Blend the tail into the head so the loop boundary is continuous."""
    ov = int(overlap_s * SR)
    t = np.linspace(0.0, 1.0, ov)
    x[-ov:] = x[-ov:] * (1.0 - t) + x[:ov] * t
    return x


def main() -> None:
    rng = np.random.default_rng(20260809)
    n = int(SR * DUR)
    t = np.arange(n) / SR

    # River body: brown noise (integrated white) -> 120-1800 Hz wash.
    brown = np.cumsum(rng.normal(0.0, 1.0, n))
    brown -= np.mean(brown)
    river = band_filter(brown, 120.0, 1800.0, rolloff=1.5)
    river /= np.max(np.abs(river))

    # Spray: white noise -> 2500-6500 Hz hiss, amplitude-pulsed.
    spray = band_filter(rng.normal(0.0, 1.0, n), 2500.0, 6500.0, rolloff=2.0)
    spray /= np.max(np.abs(spray))
    pulse = 0.55 + 0.45 * np.sin(2.0 * np.pi * 1.7 * t + 0.4)
    pulse *= 0.5 + 0.5 * np.sin(2.0 * np.pi * 0.8 * t)
    spray *= np.clip(pulse, 0.05, 1.0)

    # Wind: slow lowpassed noise with a gentle 0.12 Hz swell.
    wind = np.cumsum(rng.normal(0.0, 1.0, n))
    wind -= np.mean(wind)
    wind = band_filter(wind, 0.0, 300.0, rolloff=2.0)
    wind /= np.max(np.abs(wind))
    swell = 0.5 + 0.5 * np.sin(2.0 * np.pi * 0.12 * t + 1.2)
    wind *= swell

    mix = river * 0.62 + spray * 0.2 + wind * 0.18
    mix = seamless(mix, 1.0)
    mix = np.tanh(mix * 1.4)
    mix /= np.max(np.abs(mix))
    mix *= 0.42  # gentle ambience level

    pcm = (mix * 32767.0).astype(np.int16)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(OUT), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    print(f"wrote {OUT} ({DUR}s, mono {SR}Hz)")


if __name__ == "__main__":
    main()
