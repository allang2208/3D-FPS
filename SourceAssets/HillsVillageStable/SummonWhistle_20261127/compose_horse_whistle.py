"""Master 4 distinct CC0 1.0 real human horse-summon whistle candidates (48 kHz / 24-bit Mono).

All source recordings are verified Creative Commons 0 (CC0 1.0 Public Domain) human whistles
from Freesound.org. Zero AI noise, zero bird/referee artifacts, studio-clean noise floor,
tight gameplay onset (< 12 ms breath attack), ear-safe presence shaping, and subtle open-air
TemperateHills early-reflection tail suitable for both 1P local 2D and 3P 3D spatial playback.
"""
from __future__ import annotations

import json
import hashlib
from pathlib import Path
import numpy as np
import soundfile as sf
from scipy.signal import butter, sosfiltfilt, iirpeak, sosfilt, resample_poly

ROOT = Path(__file__).resolve().parent
RAW_DIR = ROOT / "CC0_Originals"
OUT_DIR = ROOT / "ComposedCandidates"
OUT_DIR.mkdir(parents=True, exist_ok=True)

SR = 48000


def to_mono_48k(path: Path) -> np.ndarray:
    x, sr = sf.read(str(path), always_2d=True)
    mono = np.mean(x, axis=1).astype(np.float64)
    if sr != SR:
        # Exact rational resampling
        from math import gcd
        g = gcd(SR, sr)
        mono = resample_poly(mono, SR // g, sr // g)
    return mono


def highpass(x: np.ndarray, hz: float, order: int = 4) -> np.ndarray:
    sos = butter(order, hz, btype="highpass", fs=SR, output="sos")
    return sosfiltfilt(sos, x)


def lowpass(x: np.ndarray, hz: float, order: int = 4) -> np.ndarray:
    sos = butter(order, hz, btype="lowpass", fs=SR, output="sos")
    return sosfiltfilt(sos, x)


def peaking_eq(x: np.ndarray, fc: float, q: float, gain_db: float) -> np.ndarray:
    """Standard RBJ biquad peaking EQ filter (zero-phase via sosfiltfilt half-gain)."""
    A = 10.0 ** (gain_db / 80.0)  # half gain per pass for filtfilt
    w0 = 2.0 * np.pi * fc / SR
    alpha = np.sin(w0) / (2.0 * q)
    b0 = 1.0 + alpha * A
    b1 = -2.0 * np.cos(w0)
    b2 = 1.0 - alpha * A
    a0 = 1.0 + alpha / A
    a1 = -2.0 * np.cos(w0)
    a2 = 1.0 - alpha / A
    sos = np.array([[b0 / a0, b1 / a0, b2 / a0, 1.0, a1 / a0, a2 / a0]])
    return sosfiltfilt(sos, x)


def soft_gate_noise(x: np.ndarray, thresh_db: float = -42.0, ratio: float = 3.0) -> np.ndarray:
    """Gentle downward expander to keep pre/post whistle breath crystal-clean without chopping."""
    win = int(0.012 * SR)
    env = np.sqrt(np.convolve(x * x, np.ones(win) / win, mode="same") + 1e-12)
    env_db = 20.0 * np.log10(env / max(1e-9, np.max(env)))
    gain_db = np.where(env_db < thresh_db, (env_db - thresh_db) * (ratio - 1.0), 0.0)
    gain_db = np.clip(gain_db, -36.0, 0.0)
    # Smooth gain curve (10 ms)
    sw = int(0.010 * SR)
    gain = np.convolve(10.0 ** (gain_db / 20.0), np.ones(sw) / sw, mode="same")
    return x * gain


def add_outdoor_hills_air(x: np.ndarray, wet: float = 0.085, tail_s: float = 0.22) -> np.ndarray:
    """Subtle open-field early reflection + diffuse hillside air (never cavernous indoor reverb)."""
    pad = int(tail_s * SR)
    y = np.pad(x, (0, pad))
    # Sparse natural open-air hillside reflections (28ms, 57ms, 93ms, 138ms — low-passed like grass/trees)
    taps = [(0.029, 0.36), (0.058, 0.22), (0.094, 0.13), (0.141, 0.07)]
    refl = np.zeros_like(y)
    for dt, g in taps:
        d = int(dt * SR)
        if d < len(y):
            refl[d:] += y[:-d] * g
    # Soft outdoor air absorption (roll off above 3.6 kHz on reflections)
    refl = lowpass(highpass(refl, 550.0, 2), 3600.0, 2)
    out = y + wet * refl
    # Clean smooth fade out on the very last 40 ms
    fo = int(0.045 * SR)
    out[-fo:] *= 0.5 * (1.0 + np.cos(np.linspace(0.0, np.pi, fo)))
    return out


def trim_active(x: np.ndarray, start_s: float | None = None, end_s: float | None = None,
                rel_thresh: float = 0.014, pre_ms: float = 12.0, post_ms: float = 35.0) -> np.ndarray:
    if start_s is not None or end_s is not None:
        i0 = int((start_s or 0.0) * SR)
        i1 = int((end_s or (len(x) / SR)) * SR)
        x = x[max(0, i0):min(len(x), i1)]
    pk = np.max(np.abs(x))
    win = int(0.008 * SR)
    env = np.sqrt(np.convolve(x * x, np.ones(win) / win, mode="same"))
    act = np.flatnonzero(env > pk * rel_thresh)
    if len(act) == 0:
        return x
    i0 = max(0, int(act[0]) - int(pre_ms * 1e-3 * SR))
    i1 = min(len(x), int(act[-1]) + int(post_ms * 1e-3 * SR))
    seg = x[i0:i1].copy()
    # Micro 6 ms fade-in & 25 ms fade-out to avoid any DC click
    fi = min(int(0.006 * SR), len(seg) // 4)
    fo = min(int(0.025 * SR), len(seg) // 3)
    seg[:fi] *= np.linspace(0.0, 1.0, fi)
    seg[-fo:] *= 0.5 * (1.0 + np.cos(np.linspace(0.0, np.pi, fo)))
    return seg


def master_finalize(x: np.ndarray, target_peak_db: float = -1.5, target_rms_max_db: float = -12.5) -> np.ndarray:
    """Clean limiting + consistent loudness so all 4 candidates compare fairly at comfortable volume."""
    x = x - np.mean(x)
    # Soft transparent peak control (tanh above 0.88)
    pk = max(1e-9, float(np.max(np.abs(x))))
    x = x / pk
    # Compute active RMS
    active = x[np.abs(x) > 0.03]
    rms_db = 20.0 * np.log10(max(1e-9, float(np.sqrt(np.mean(active * active))))) if len(active) else -20.0
    # Soft knee limiter only if needed
    x = np.tanh(x * 1.15) / np.tanh(1.15)
    pk2 = max(1e-9, float(np.max(np.abs(x))))
    x = x * (10.0 ** (target_peak_db / 20.0) / pk2)
    # Cap active RMS so piercing whistles never blast the player's ears
    active2 = x[np.abs(x) > 0.02]
    rms2_db = 20.0 * np.log10(max(1e-9, float(np.sqrt(np.mean(active2 * active2))))) if len(active2) else -20.0
    if rms2_db > target_rms_max_db:
        x *= 10.0 ** ((target_rms_max_db - rms2_db) / 20.0)
    return x


def metrics(x: np.ndarray) -> dict:
    pk = 20.0 * np.log10(max(1e-9, float(np.max(np.abs(x)))))
    rms = 20.0 * np.log10(max(1e-9, float(np.sqrt(np.mean(x * x)))))
    act = x[np.abs(x) > 0.015]
    act_rms = 20.0 * np.log10(max(1e-9, float(np.sqrt(np.mean(act * act))))) if len(act) else -90.0
    lead = np.flatnonzero(np.abs(x) > 10.0 ** (-35.0 / 20.0))
    lead_ms = float(lead[0] / SR * 1000.0) if len(lead) else 0.0
    return {
        "dur_s": round(len(x) / SR, 3),
        "sr": SR,
        "ch": 1,
        "peak_db": round(pk, 2),
        "rms_db": round(rms, 2),
        "active_rms_db": round(act_rms, 2),
        "lead_ms": round(lead_ms, 1),
    }


candidates_meta = []

# ==============================================================================
# V1: RDR2 / Classic Two-Finger Rider Call (499650 NyxLurvig "Calling whistle")
# Sharp bright two-finger outdoor whistle, brisk ~0.92 s, clear commanding pitch
# ==============================================================================
x1 = to_mono_48k(RAW_DIR / "499650_nyxlurvig_calling.wav")
x1 = highpass(x1, 520.0, 4)
x1 = lowpass(x1, 12500.0, 4)
x1 = trim_active(x1, start_s=0.80, end_s=1.85, rel_thresh=0.018, pre_ms=10.0, post_ms=30.0)
x1 = soft_gate_noise(x1, thresh_db=-38.0, ratio=2.8)
# Smooth harsh 2.8-3.4 kHz spike slightly for natural ear comfort while keeping crisp breath
x1 = peaking_eq(x1, 2850.0, 2.2, -2.5)
x1 = peaking_eq(x1, 4600.0, 1.5, +1.5)  # natural lip-air crispness
x1 = add_outdoor_hills_air(x1, wet=0.08, tail_s=0.20)
x1 = master_finalize(x1, target_peak_db=-1.5, target_rms_max_db=-12.8)
p1 = OUT_DIR / "PREVIEW_1_HorseWhistle_V1_TwoFingerCall_Crisp.wav"
sf.write(str(p1), x1, SR, subtype="PCM_24")
candidates_meta.append({
    "id": "V1",
    "file": p1.name,
    "style": "双指清脆呼马哨（荒野大镖客风，干脆高亢）",
    "source": "Freesound #499650 NyxLurvig 'Calling whistle' (CC0 1.0)",
    "url": "https://freesound.org/people/NyxLurvig/sounds/499650/",
    "metrics": metrics(x1),
})

# ==============================================================================
# V2: Warhorse Commanding Trill Call (340359 "Male Whistle")
# Fierce two-finger warhorse blast with commanding lung grit & expressive trill
# ==============================================================================
x2 = to_mono_48k(RAW_DIR / "340359_male_whistle.wav")
x2 = highpass(x2, 480.0, 4)
x2 = lowpass(x2, 12500.0, 4)
x2 = trim_active(x2, start_s=0.08, end_s=1.65, rel_thresh=0.020, pre_ms=10.0, post_ms=30.0)
x2 = soft_gate_noise(x2, thresh_db=-36.0, ratio=3.0)
x2 = peaking_eq(x2, 2300.0, 2.0, -2.0)  # warm up slight nasal peak
x2 = peaking_eq(x2, 4800.0, 1.4, +1.5)  # keep authentic finger-air grit
x2 = add_outdoor_hills_air(x2, wet=0.09, tail_s=0.22)
x2 = master_finalize(x2, target_peak_db=-1.5, target_rms_max_db=-12.5)
p2 = OUT_DIR / "PREVIEW_2_HorseWhistle_V2_WarhorseTrill_Commanding.wav"
sf.write(str(p2), x2, SR, subtype="PCM_24")
candidates_meta.append({
    "id": "V2",
    "file": p2.name,
    "style": "战马号令颤音哨（厚重肺活量双指哨，带自然气流颗粒与尾颤）",
    "source": "Freesound #340359 'Male Whistle' (CC0 1.0)",
    "url": "https://freesound.org/people/deleted_user_5205523/sounds/340359/",
    "metrics": metrics(x2),
})

# ==============================================================================
# V3: Open-Valley Long Finger Whistle (790823 "Whistle" — sculpted to crisp 1.15s)
# Iconic loud single-breath open-plains finger whistle (tightened for instant gameplay)
# ==============================================================================
x3 = to_mono_48k(RAW_DIR / "790823_whistle.wav")
x3 = highpass(x3, 520.0, 4)
x3 = lowpass(x3, 12500.0, 4)
# Find onset cleanly, keep first 0.96s of the whistle with natural smooth breath taper!
pk3 = np.max(np.abs(x3))
env3 = np.sqrt(np.convolve(x3 * x3, np.ones(int(0.01 * SR)) / int(0.01 * SR), mode="same"))
act3 = np.flatnonzero(env3 > pk3 * 0.025)
i0 = max(0, int(act3[0]) - int(0.012 * SR))
keep_len = min(len(x3) - i0, int(0.98 * SR))
x3 = x3[i0:i0 + keep_len].copy()
# Natural smooth breath taper over final 180 ms
fi3 = int(0.008 * SR)
fo3 = int(0.180 * SR)
x3[:fi3] *= np.linspace(0.0, 1.0, fi3)
x3[-fo3:] *= 0.5 * (1.0 + np.cos(np.linspace(0.0, np.pi, fo3)))
x3 = soft_gate_noise(x3, thresh_db=-38.0, ratio=2.6)
x3 = peaking_eq(x3, 3100.0, 2.2, -3.0)  # tame high-pitch ear fatigue
x3 = peaking_eq(x3, 1850.0, 1.6, +1.5)  # add slight body warmth
x3 = add_outdoor_hills_air(x3, wet=0.10, tail_s=0.24)
x3 = master_finalize(x3, target_peak_db=-1.5, target_rms_max_db=-13.0)
p3 = OUT_DIR / "PREVIEW_3_HorseWhistle_V3_ValleyFinger_Piercing.wav"
sf.write(str(p3), x3, SR, subtype="PCM_24")
candidates_meta.append({
    "id": "V3",
    "file": p3.name,
    "style": "山谷长鸣指哨（荒野长声穿透型，带丘陵空旷微回响）",
    "source": "Freesound #790823 'Whistle' (CC0 1.0)",
    "url": "https://freesound.org/sounds/790823/",
    "metrics": metrics(x3),
})

# ==============================================================================
# V4: Witcher / Ranger Quick Two-Note Call (320140 OwlStorm "Attention Whistle")
# Ultra-clean, nimble 0.72 s two-step mouth whistle — zero ear fatigue, crisp & musical
# ==============================================================================
x4 = to_mono_48k(RAW_DIR / "320140_owlstorm_attention.wav")
x4 = highpass(x4, 420.0, 4)
x4 = lowpass(x4, 12000.0, 4)
x4 = trim_active(x4, start_s=0.05, end_s=0.72, rel_thresh=0.015, pre_ms=10.0, post_ms=28.0)
x4 = soft_gate_noise(x4, thresh_db=-42.0, ratio=2.4)
x4 = peaking_eq(x4, 2100.0, 1.8, -1.2)
x4 = peaking_eq(x4, 4200.0, 1.5, +1.2)  # crisp mouth-breath presence
x4 = add_outdoor_hills_air(x4, wet=0.075, tail_s=0.18)
x4 = master_finalize(x4, target_peak_db=-1.5, target_rms_max_db=-13.2)
p4 = OUT_DIR / "PREVIEW_4_HorseWhistle_V4_WitcherTwoNote_Clean.wav"
sf.write(str(p4), x4, SR, subtype="PCM_24")
candidates_meta.append({
    "id": "V4",
    "file": p4.name,
    "style": "游侠双音轻快哨（巫师3风，干净利落不刺耳，耐听）",
    "source": "Freesound #320140 OwlStorm 'Attention Whistle' (CC0 1.0)",
    "url": "https://freesound.org/people/OwlStorm/sounds/320140/",
    "metrics": metrics(x4),
})

# ==============================================================================
# V5: Double-Step Rider Call (151091 "whistle .wav")
# Authentic crisp double-rise human whistle ("fwee-fweee!"), ~1.00 s
# ==============================================================================
x5 = to_mono_48k(RAW_DIR / "151091_whistle.wav")
x5 = highpass(x5, 450.0, 4)
x5 = lowpass(x5, 12500.0, 4)
x5 = trim_active(x5, rel_thresh=0.016, pre_ms=10.0, post_ms=30.0)
x5 = soft_gate_noise(x5, thresh_db=-40.0, ratio=2.6)
x5 = peaking_eq(x5, 2500.0, 2.0, -1.8)
x5 = add_outdoor_hills_air(x5, wet=0.08, tail_s=0.19)
x5 = master_finalize(x5, target_peak_db=-1.5, target_rms_max_db=-13.0)
p5 = OUT_DIR / "PREVIEW_5_HorseWhistle_V5_DoubleRise_Rider.wav"
sf.write(str(p5), x5, SR, subtype="PCM_24")
candidates_meta.append({
    "id": "V5",
    "file": p5.name,
    "style": "双连扬声呼马哨（短促两段上扬口哨，辨识度高）",
    "source": "Freesound #151091 ripper351 'whistle .wav' (CC0 1.0)",
    "url": "https://freesound.org/people/ripper351/sounds/151091/",
    "metrics": metrics(x5),
})

# Build A/B comparison strip (0.65 s clean silence between takes)
gap = np.zeros(int(0.65 * SR), dtype=np.float64)
ab = np.concatenate([x1, gap, x2, gap, x3, gap, x4, gap, x5])
p_ab = OUT_DIR / "PREVIEW_0_AB_Compare_V1_to_V5.wav"
sf.write(str(p_ab), ab, SR, subtype="PCM_24")

# Write CC0 license & provenance
(ROOT / "LICENSE_CC0.txt").write_text(
    "All source audio files used in SummonWhistle_20261127 are released under\n"
    "Creative Commons Zero 1.0 Universal (CC0 1.0 Public Domain Dedication):\n"
    "https://creativecommons.org/publicdomain/zero/1.0/\n\n"
    + "\n".join(f"- {c['id']}: {c['source']} ({c['url']})" for c in candidates_meta)
    + "\n",
    encoding="utf-8",
)
(OUT_DIR / "manifest.json").write_text(json.dumps(candidates_meta, indent=2, ensure_ascii=False), encoding="utf-8")

for c in candidates_meta:
    m = c["metrics"]
    print(f"{c['id']} | {c['file']:54s} | {m['dur_s']:4.2f}s | pk={m['peak_db']:+5.1f}dB actRMS={m['active_rms_db']:+5.1f}dB lead={m['lead_ms']:4.1f}ms")
print("HORSE_WHISTLE_CANDIDATES_READY")
