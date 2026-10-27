"""Rebalance the selected release: E/F detail forward, G reduced and shortened."""
from pathlib import Path
import hashlib
import json

import numpy as np
import soundfile as sf
from scipy.signal import butter, sosfilt

ROOT = Path(__file__).resolve().parent
INPUT = ROOT.parent / "Singles"
RATE = 48000
LENGTH = .86


def filtered(x, frequency, kind):
    return sosfilt(butter(2, frequency, btype=kind, fs=RATE, output="sos"), x, axis=0)


def decay_after(x, start, end):
    t = np.arange(len(x)) / RATE
    progress = np.clip((t - start) / (end - start), 0, 1)
    envelope = np.cos(progress * np.pi / 2) ** 2
    return x * envelope[:, None]


def main():
    names = {"E": "E_HeavySnap.wav", "F": "F_PiercingRip.wav", "G": "G_SiegeBurst.wav"}
    sources, records = {}, []
    for key, name in names.items():
        path = INPUT / name
        samples, rate = sf.read(path, dtype="float64", always_2d=True)
        if rate != RATE or samples.shape[1] != 2:
            raise ValueError(f"Expected the authored 48 kHz stereo candidate: {name}")
        sources[key] = samples
        records.append({"candidate": key, "file": "../Singles/" + name,
                        "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})

    # Restore E's upper string detail and F's low-mid texture removed by V3's split.
    e = filtered(sources["E"], 80, "highpass")
    f = filtered(sources["F"], 180, "highpass")
    ramp = round(.002 * RATE)
    f[:ramp] *= np.linspace(.7, 1, ramp)[:, None]
    # G is a quiet, early weight layer; its late boom/air tail no longer follows E/F.
    g = filtered(sources["G"], [45, 500], "bandpass")
    g = decay_after(g, .065, .24)
    layers = [(e, 1., 0.), (f, .82, .006), (g, .38, .002)]
    mixed = np.zeros((round(LENGTH * RATE), 2))
    for x, gain, delay in layers:
        start = round(delay * RATE)
        count = min(len(x), len(mixed) - start)
        mixed[start:start + count] += gain * x[:count]
    mixed = filtered(mixed, 35, "highpass")
    # No extra master saturation: preserve E/F transient detail already present in the stems.
    mixed = decay_after(mixed, .62, .84)
    attack = round(.0005 * RATE)
    mixed[:attack] *= np.linspace(0, 1, attack)[:, None]
    master_gain = 10 ** (-3 / 20) / max(1.e-9, float(np.max(np.abs(mixed))))
    mixed *= master_gain
    single = ROOT / "H_HeartPiercing_BalancedV4.wav"
    audition = ROOT / "H_HeartPiercing_BalancedV4_2x.wav"
    sf.write(single, mixed, RATE, subtype="PCM_24")
    gap = np.zeros((round(.85 * RATE), 2))
    tail = np.zeros((round(.25 * RATE), 2))
    sf.write(audition, np.concatenate((mixed, gap, mixed, tail)), RATE, subtype="PCM_16")
    manifest = {
        "candidate": "H", "revision": "BalancedV4", "source_candidates": records,
        "user_request": "Reduce the excessive third sound and include the first two sounds' detail",
        "layers": [
            {"source": "E", "highpass_hz": 80, "gain": 1., "delay_seconds": 0},
            {"source": "F", "highpass_hz": 180, "gain": .82, "delay_seconds": .006, "attack_ramp_seconds": .002},
            {"source": "G", "band_hz": [45, 500], "gain": .38, "delay_seconds": .002,
             "fade_start_seconds": .065, "fade_end_seconds": .24},
        ],
        "g_layer_gain_change_db_from_v3": float(20 * np.log10(.38 / 1.30)),
        "g_high_air_tail_removed": True,
        "master": "35 Hz high-pass; no added saturation; 0.5 ms attack; 620-840 ms fade; -3 dBFS sample peak",
        "master_gain_db": float(20 * np.log10(master_gain)),
        "sample_rate": RATE, "channels": 2, "single_seconds": LENGTH,
        "single": single.name, "audition": audition.name,
        "audition_repeats": 2, "audition_gap_seconds": .85,
        "license": "CC0-1.0; source credits and license chain in ../README.md",
        "listening_approved": False, "game_tested": False,
    }
    (ROOT / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"single": str(single), "audition": str(audition), "seconds": LENGTH}, ensure_ascii=True))


if __name__ == "__main__":
    main()
