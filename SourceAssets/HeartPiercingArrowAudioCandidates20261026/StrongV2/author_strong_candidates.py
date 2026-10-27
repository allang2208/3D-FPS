"""Layered release-only audition sounds. No Unreal assets or runtime bindings."""
from pathlib import Path
import hashlib
import json
import math

import numpy as np
import soundfile as sf
from scipy.signal import butter, resample_poly, sosfilt

ROOT = Path(__file__).resolve().parent
SOURCES = ROOT.parent / "Sources"
RATE = 48000
RNG = np.random.default_rng(261026)
SOURCE_FILES = ["Bow.wav", "English_Longbow_Shoot.wav", "swish_2.wav", "swish_3.wav", "swish_4.wav"]


def stereo(x):
    return np.repeat(x[:, None], 2, axis=1) if x.ndim == 1 else x


def normalize(x):
    return x / max(1.e-9, float(np.max(np.abs(x))))


def edges(x, attack=.001, release=.018):
    x = x.copy()
    a, b = min(len(x), round(attack * RATE)), min(len(x), round(release * RATE))
    x[:a] *= np.linspace(0, 1, a)[:, None]
    x[-b:] *= np.linspace(1, 0, b)[:, None]
    return x


def filt(x, frequency, kind):
    return sosfilt(butter(2, frequency, btype=kind, fs=RATE, output="sos"), x, axis=0)


def load(name, start, end, speed=1.):
    x, sr = sf.read(SOURCES / name, dtype="float64", always_2d=True)
    x = x[round(start * sr):round(end * sr)]
    if x.shape[1] == 1:
        x = np.repeat(x, 2, axis=1)
    effective = round(sr * speed)
    common = math.gcd(effective, RATE)
    x = resample_poly(x, RATE // common, effective // common, axis=0)
    return normalize(edges(filt(x, 65, "highpass")))


def body(seconds, high, low, decay):
    t = np.arange(round(seconds * RATE)) / RATE
    hz = low + (high - low) * np.exp(-t / .022)
    phase = 2 * np.pi * np.cumsum(hz) / RATE
    x = np.sin(phase) + .32 * np.sin(2 * phase) + .10 * np.sin(3 * phase)
    x *= (1 - np.exp(-t / .0015)) * np.exp(-t / decay)
    return normalize(edges(stereo(x), .0005, .035))


def pressure(seconds, bands, decay):
    t = np.arange(round(seconds * RATE)) / RATE
    x = stereo(RNG.normal(0, 1, len(t)))
    x = filt(x, bands, "bandpass")
    x *= ((1 - np.exp(-t / .0008)) * np.exp(-t / decay))[:, None]
    return normalize(edges(x, .0004, .012))


def mix(length, layers):
    out = np.zeros((round(length * RATE), 2))
    for x, gain, delay in layers:
        begin = round(delay * RATE)
        count = min(len(x), len(out) - begin)
        out[begin:begin + count] += gain * x[:count]
    return out


def reflections(x, taps):
    out = x.copy()
    softened = filt(x, 3200, "lowpass")
    for delay, gain in taps:
        offset = round(delay * RATE)
        out[offset:] += softened[:-offset, ::-1] * gain
    return out


def export(letter, label, title, x, recipe):
    # Mild saturation increases body density while preserving a shared peak ceiling.
    x = filt(x, 38, "highpass")
    x = np.tanh(x * .85)
    x = edges(x, .0005, .05)
    x = normalize(x) * 10 ** (-3 / 20)
    single = ROOT / "Singles" / f"{letter}_{label}.wav"
    preview = ROOT / "Auditions" / f"{letter}_{label}_2x.wav"
    sf.write(single, x, RATE, subtype="PCM_24")
    gap = np.zeros((round(.85 * RATE), 2))
    tail = np.zeros((round(.25 * RATE), 2))
    sf.write(preview, np.concatenate((x, gap, x, tail)), RATE, subtype="PCM_16")
    return {
        "candidate": letter, "title": title,
        "single": str(single.relative_to(ROOT)), "audition": str(preview.relative_to(ROOT)),
        "seconds": len(x) / RATE, "recipe": recipe,
        "peak_target_dbfs": -3, "selected": False, "imported_to_ue": False,
    }


def main():
    for name in ("Singles", "Auditions"):
        (ROOT / name).mkdir(exist_ok=True)
    e = mix(.68, [
        (load("Bow.wav", .102, .36, .78), .95, 0),
        (load("English_Longbow_Shoot.wav", .101, .49, .88), .40, .003),
        (body(.32, 145, 70, .065), .72, .003),
        (pressure(.11, [160, 1700], .018), .30, .001),
        (load("swish_2.wav", .049, .30, 1.12), .34, .014),
    ])
    f = mix(.76, [
        (load("Bow.wav", .103, .32, 1.10), .85, 0),
        (load("English_Longbow_Shoot.wav", .101, .43, .90), .38, .002),
        (body(.28, 190, 73, .052), .62, .002),
        (pressure(.09, [700, 7500], .012), .40, .001),
        (normalize(filt(load("swish_3.wav", .009, .43, 1.12), [650, 8500], "bandpass")), .65, .008),
    ])
    f = reflections(f, [(.043, .075), (.079, .045)])
    g = mix(.98, [
        (load("Bow.wav", .102, .37, .70), .82, 0),
        (load("English_Longbow_Shoot.wav", .101, .50, .76), .55, .003),
        (body(.52, 185, 56, .13), .88, .003),
        (pressure(.17, [95, 1800], .035), .48, .002),
        (load("swish_4.wav", .064, .31, .90), .46, .012),
        (normalize(filt(load("swish_3.wav", .015, .42, .88), 800, "highpass")), .24, .065),
    ])
    g = reflections(g, [(.091, .10), (.163, .06), (.241, .025)])
    entries = [
        export("E", "HeavySnap", "重弦崩响", e, "Lowered bow/string layers + short low-body impulse + short pressure transient + fast swish. Compact tail."),
        export("F", "PiercingRip", "裂空穿刺", f, "Sharp bow attack + bright air rip + brief low-body impulse + quiet early reflections."),
        export("G", "SiegeBurst", "蓄力震爆", g, "Lower bow body + stronger descending bass impulse + broad pressure transient + longer airy release and short reflections."),
    ]
    manifest = {
        "purpose": "User-requested stronger heart-piercing-arrow auditions; layered sound design, not raw recordings",
        "sample_rate": RATE, "channels": 2, "rng_seed": 261026,
        "runtime_modified": False, "game_tested": False, "listening_approved": False,
        "loudness_note": "Shared -3 dBFS sample peak; no claim of perceptual loudness matching. Changes are attack, layering, spectral body and tail, not master gain alone.",
        "sources": [{"file": str((SOURCES / n).relative_to(ROOT.parent)), "sha256": hashlib.sha256((SOURCES / n).read_bytes()).hexdigest(), "license": "CC0-1.0"} for n in SOURCE_FILES],
        "candidates": entries,
    }
    (ROOT / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    for item in entries:
        print(json.dumps(item, ensure_ascii=False))


if __name__ == "__main__":
    main()
