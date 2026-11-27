"""Compose 3 high-impact 48 kHz / 24-bit True Stereo HeartPiercingArrow (穿心箭) release candidates.

Fuses bespoke Colab L4 MMAudio (large_44k_v2) sonic-bow/air-tear/shockwave stems with real CC0
recorded bowstring & longbow stems (Bow.wav, English_Longbow_Shoot.wav, S_BowVideoDirect_Release.wav,
swish_2/3/4.wav) and Ballista torsion snap for zero-latency (<2 ms) AAA cinematic impact.

Runtime target:
  /Game/Skills/HeartPiercingArrow/Audio20261026/S_HeartPiercingArrow_Release
  Played on 3-second full-charge release (2.5x+ damage, 2.0x arrow speed, up to 3 enemy penetrations).

Candidates:
  - V1_SonicArmorPiercer       (1.15 s): Crisp heavy warbow snap + supersonic air-shatter + tight chest punch + steel ring
  - V2_ThunderWarbow_Shockwave (1.30 s): Maximum seismic greatbow pressure shockwave + heavy torsion slam + roaring wind wake
  - V3_DragonPiercer_RazorWind (1.20 s): Monster Hunter Dragon Piercer style — blinding speed, razor wind vortex & supersonic crack
"""

from __future__ import annotations

import hashlib
import json
import math
import wave
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import soundfile as sf
from scipy import signal

SR = 48000
SKILL_ROOT = Path(r"D:\FPS3D\FPSGAME\SourceAssets\HeartPiercingArrowAudioCandidates20261026")
SRC_CC0 = SKILL_ROOT / "Sources"
BOW_DIRECT = Path(r"D:\FPS3D\FPSGAME\SourceAssets\BowVideoAudioDirect20260926\Wav\S_BowVideoDirect_Release.wav")
BALLISTA_TWANG = Path(r"D:\FPS3D\FPSGAME\SourceAssets\HillsVillageHighWall20261120\SiegeAudioColab20261126\B10_BallistaTwangBolt\Candidates\B10_BallistaTwangBolt_01_s8001.wav")
COLAB = SKILL_ROOT / "ColabImpactV2_20261126"
OUT = COLAB / "ComposedCandidates"

_CACHE: Dict[str, np.ndarray] = {}


def load_48k_stereo(path: Path) -> np.ndarray:
    key = str(path.resolve())
    if key in _CACHE:
        return _CACHE[key]
    x, src_sr = sf.read(str(path), always_2d=True, dtype="float64")
    if x.shape[1] == 1:
        x = np.repeat(x, 2, axis=1)
    else:
        x = x[:, :2]
    x = x.T
    x = x - np.mean(x, axis=1, keepdims=True)
    if src_sr != SR:
        g = math.gcd(src_sr, SR)
        x = signal.resample_poly(x, SR // g, src_sr // g, axis=1)
    _CACHE[key] = x
    return x


def auto_trim_onset(x: np.ndarray, pre_ms: float = 1.5, thr_rel: float = 0.08, search_after_s: float = 0.0) -> np.ndarray:
    """Align the primary transient onset cleanly to t=0 so every layer stacks with millisecond precision."""
    mono = np.abs(x.mean(axis=0))
    i_min = int(round(search_after_s * SR))
    sub = mono[i_min:]
    pk = float(np.max(sub) + 1e-12)
    idx_pk = i_min + int(np.argmax(sub))
    # Walk backwards from peak to onset threshold
    i0 = idx_pk
    for k in range(idx_pk, max(i_min, idx_pk - int(0.08 * SR)), -1):
        if mono[k] < thr_rel * pk:
            i0 = k
            break
    i0 = max(0, i0 - int(round(pre_ms * 0.001 * SR)))
    return x[:, i0:].copy()


def pitch_speed(x: np.ndarray, ratio: float) -> np.ndarray:
    if abs(ratio - 1.0) < 1e-4:
        return x.copy()
    up = int(round(1000 / ratio))
    down = 1000
    g = math.gcd(up, down)
    return signal.resample_poly(x, up // g, down // g, axis=1)


def widen_mono_subtle(x: np.ndarray, delay_ms: float = 0.45, depth: float = 0.22) -> np.ndarray:
    """Create natural true-stereo spaciousness on mono stems without phase hollowing in mono fold-down."""
    # Complementary comb-free mid-side Haas + slight high-band stereo air
    d = max(1, int(round(delay_ms * 0.001 * SR)))
    mid = 0.5 * (x[0] + x[1])
    # Side from high-passed gently delayed difference (kept >350 Hz so sub-bass stays 100% mono-centered!)
    hi = hp(np.stack([mid, mid], axis=0), 380.0, order=2)[0]
    side = np.zeros_like(mid)
    side[d:] = (hi[:-d] - hi[d:]) * depth
    return np.stack([mid + side, mid - side], axis=0)


def slice_dur(x: np.ndarray, dur_s: float, speed: float = 1.0, fade_in_ms: float = 0.6, fade_out_ms: float = 45.0) -> np.ndarray:
    seg = pitch_speed(x, speed) if abs(speed - 1.0) > 1e-4 else x.copy()
    n = max(16, int(round(dur_s * SR)))
    seg = seg[:, :n] if seg.shape[1] >= n else np.pad(seg, ((0, 0), (0, n - seg.shape[1])))
    fi = min(seg.shape[1] // 2, int(round(fade_in_ms * 0.001 * SR)))
    fo = min(seg.shape[1] // 2, int(round(fade_out_ms * 0.001 * SR)))
    if fi > 1:
        seg[:, :fi] *= 0.5 * (1.0 - np.cos(np.pi * np.linspace(0.0, 1.0, fi)))
    if fo > 1:
        seg[:, -fo:] *= 0.5 * (1.0 + np.cos(np.pi * np.linspace(0.0, 1.0, fo)))
    return seg


def norm(x: np.ndarray, peak: float = 0.92) -> np.ndarray:
    return x * (peak / float(np.max(np.abs(x)) + 1e-12))


def hp(x: np.ndarray, hz: float, order: int = 2) -> np.ndarray:
    return signal.sosfiltfilt(signal.butter(order, hz / (SR * 0.5), btype="highpass", output="sos"), x, axis=1)


def lp(x: np.ndarray, hz: float, order: int = 2) -> np.ndarray:
    return signal.sosfiltfilt(signal.butter(order, min(hz, SR * 0.48) / (SR * 0.5), btype="lowpass", output="sos"), x, axis=1)


def bp(x: np.ndarray, lo: float, hi: float, order: int = 2) -> np.ndarray:
    return signal.sosfiltfilt(signal.butter(order, [lo / (SR * 0.5), min(hi, SR * 0.48) / (SR * 0.5)], btype="bandpass", output="sos"), x, axis=1)


def shelf_low(x: np.ndarray, hz: float, db: float) -> np.ndarray:
    return x + (10.0 ** (db / 20.0) - 1.0) * lp(x, hz, order=2)


def shelf_high(x: np.ndarray, hz: float, db: float) -> np.ndarray:
    return x + (10.0 ** (db / 20.0) - 1.0) * hp(x, hz, order=2)


def peak_eq(x: np.ndarray, lo: float, hi: float, db: float) -> np.ndarray:
    return x + (10.0 ** (db / 20.0) - 1.0) * bp(x, lo, hi, order=2)


def mono_sub_below(x: np.ndarray, hz: float = 140.0) -> np.ndarray:
    """Keep deep sub-bass 100% phase-locked center for maximum chest impact."""
    sub = lp(x, hz, order=2)
    hi = x - sub
    sub_m = 0.5 * (sub[0] + sub[1])
    return np.stack([sub_m, sub_m], axis=0) + hi


def synth_sub_punch(dur_s: float = 0.36, f_start: float = 155.0, f_end: float = 42.0, tau_f: float = 0.042, tau_a: float = 0.105) -> np.ndarray:
    """Clean physical kinetic sub-bass transient punch (adds zero noise, pure chest thump!)."""
    n = int(round(dur_s * SR))
    t = np.arange(n, dtype=np.float64) / SR
    # Exponential pitch drop from 155 Hz -> 42 Hz
    freq = f_end + (f_start - f_end) * np.exp(-t / tau_f)
    phase = 2.0 * np.pi * np.cumsum(freq) / SR
    env = (1.0 - np.exp(-t / 0.0018)) * np.exp(-t / tau_a)
    y = np.sin(phase) * env
    # Subtle 2nd harmonic warmth right on the first 35 ms
    y += 0.28 * np.sin(2.0 * phase) * np.exp(-t / 0.025) * (1.0 - np.exp(-t / 0.0012))
    return np.stack([y, y], axis=0)


def mix_at(buf: np.ndarray, layer: np.ndarray, offset_s: float, gain: float = 1.0) -> None:
    i0 = int(round(offset_s * SR))
    if i0 >= buf.shape[1]:
        return
    if i0 < 0:
        layer = layer[:, -i0:]
        i0 = 0
    n = min(layer.shape[1], buf.shape[1] - i0)
    if n > 0:
        buf[:, i0 : i0 + n] += layer[:, :n] * gain


def master_impact(
    x: np.ndarray,
    target_rms100_db: float = -8.2,
    peak_db: float = -0.4,
    hp_hz: float = 28.0,
    fade_in_ms: float = 0.3,
    fade_out_ms: float = 85.0,
) -> np.ndarray:
    x = x - np.mean(x, axis=1, keepdims=True)
    x = hp(x, hp_hz, order=2)
    x = mono_sub_below(x, 140.0)

    ceil = 10.0 ** (peak_db / 20.0)
    knee = 0.44 * ceil
    head = ceil - knee

    mono0 = x.mean(axis=0)
    cur_r100 = float(np.sqrt(np.mean(mono0[: min(len(mono0), int(0.10 * SR))] ** 2)) + 1e-12)
    tgt_lin = 10.0 ** (target_rms100_db / 20.0)
    drive = tgt_lin / cur_r100
    for _ in range(4):
        y = x * drive
        mag = np.max(np.abs(y), axis=0)
        over = np.maximum(0.0, mag - knee)
        mapped = knee + head * np.tanh(over / head)
        gain = np.where(mag > knee, mapped / np.maximum(mag, 1e-12), 1.0)
        y = y * gain[None, :]
        m = y.mean(axis=0)
        r100 = float(np.sqrt(np.mean(m[: min(len(m), int(0.10 * SR))] ** 2)) + 1e-12)
        drive *= (tgt_lin / r100) ** 0.75

    x = hp(y, hp_hz, order=2)
    x = mono_sub_below(x, 140.0)
    pk2 = float(np.max(np.abs(x)) + 1e-12)
    if pk2 > ceil:
        x *= ceil / pk2

    fi = min(x.shape[1] // 4, int(round(fade_in_ms * 0.001 * SR)))
    fo = min(x.shape[1] // 3, int(round(fade_out_ms * 0.001 * SR)))
    if fi > 1:
        x[:, :fi] *= 0.5 * (1.0 - np.cos(np.pi * np.linspace(0.0, 1.0, fi)))
    if fo > 1:
        x[:, -fo:] *= 0.5 * (1.0 + np.cos(np.pi * np.linspace(0.0, 1.0, fo)))
    return x


def write_wav_24bit(path: Path, stereo: np.ndarray) -> Dict[str, object]:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = np.clip(stereo, -0.999999, 0.999999)
    inter = data.T.reshape(-1)
    ints = np.round(inter * 8388607.0).astype(np.int32)
    b0 = (ints & 0xFF).astype(np.uint8)
    b1 = ((ints >> 8) & 0xFF).astype(np.uint8)
    b2 = ((ints >> 16) & 0xFF).astype(np.uint8)
    packed = np.stack([b0, b1, b2], axis=-1).tobytes()
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(3)
        wf.setframerate(SR)
        wf.writeframes(packed)
    mono = data.mean(axis=0)
    pk = float(np.max(np.abs(data)) + 1e-12)
    rms = float(np.sqrt(np.mean(mono ** 2)) + 1e-12)
    r100 = float(np.sqrt(np.mean(mono[: min(len(mono), int(0.10 * SR))] ** 2)) + 1e-12)
    seg = mono[: min(len(mono), int(0.18 * SR))]
    fft = np.abs(np.fft.rfft(seg)) ** 2
    fr = np.fft.rfftfreq(len(seg), 1.0 / SR)
    tot = float(fft.sum()) + 1e-12
    sub = 100.0 * float(fft[(fr >= 25) & (fr < 120)].sum()) / tot
    lo = 100.0 * float(fft[(fr >= 120) & (fr < 350)].sum()) / tot
    mid = 100.0 * float(fft[(fr >= 350) & (fr < 2500)].sum()) / tot
    hi = 100.0 * float(fft[(fr >= 2500) & (fr < 14000)].sum()) / tot
    thr = 10.0 ** (-35.0 / 20.0)
    nz = np.where(np.abs(mono) > thr)[0]
    lead_ms = float(nz[0] / SR * 1000.0) if len(nz) else -1.0
    sha = hashlib.sha256(path.read_bytes()).hexdigest()[:16]
    return {
        "file": str(path.relative_to(OUT)).replace("\\", "/"),
        "duration_s": round(data.shape[1] / SR, 3),
        "peak_dbfs": round(20.0 * math.log10(pk), 2),
        "rms_dbfs": round(20.0 * math.log10(rms), 2),
        "rms100_dbfs": round(20.0 * math.log10(r100), 2),
        "sub_pct": round(sub, 1),
        "lo_pct": round(lo, 1),
        "mid_pct": round(mid, 1),
        "hi_pct": round(hi, 1),
        "lead_ms": round(lead_ms, 2),
        "sha256_16": sha,
    }


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)

    # Load and onset-align all verified stems
    p1_02 = widen_mono_subtle(auto_trim_onset(load_48k_stereo(COLAB / "P1_SonicBowCrack/Candidates/P1_SonicBowCrack_02_s9102.wav"), pre_ms=1.0, search_after_s=0.80), 0.45, 0.24)
    p1_03 = widen_mono_subtle(auto_trim_onset(load_48k_stereo(COLAB / "P1_SonicBowCrack/Candidates/P1_SonicBowCrack_03_s9103.wav"), pre_ms=1.0), 0.55, 0.26)
    p2_01 = widen_mono_subtle(auto_trim_onset(load_48k_stereo(COLAB / "P2_SupersonicAirTear/Candidates/P2_SupersonicAirTear_01_s9201.wav"), pre_ms=0.8), 0.35, 0.22)
    p2_02 = widen_mono_subtle(auto_trim_onset(load_48k_stereo(COLAB / "P2_SupersonicAirTear/Candidates/P2_SupersonicAirTear_02_s9202.wav"), pre_ms=1.0, search_after_s=0.45), 0.65, 0.30)
    p3_01 = auto_trim_onset(load_48k_stereo(COLAB / "P3_ShockwaveSubBoom/Candidates/P3_ShockwaveSubBoom_01_s9301.wav"), pre_ms=1.5, search_after_s=0.35)
    p3_03 = auto_trim_onset(load_48k_stereo(COLAB / "P3_ShockwaveSubBoom/Candidates/P3_ShockwaveSubBoom_03_s9303.wav"), pre_ms=1.0)
    p4_03 = widen_mono_subtle(auto_trim_onset(load_48k_stereo(COLAB / "P4_SteelTensionTwang/Candidates/P4_SteelTensionTwang_03_s9403.wav"), pre_ms=0.5, search_after_s=0.55), 0.50, 0.28)

    # Real CC0 recorded bowstring + normal game bow + arrow swishes + heavy ballista torsion snap
    cc0_bow = auto_trim_onset(load_48k_stereo(SRC_CC0 / "Bow.wav"), pre_ms=0.8)
    cc0_longbow = auto_trim_onset(load_48k_stereo(SRC_CC0 / "English_Longbow_Shoot.wav"), pre_ms=1.0, search_after_s=0.0)
    game_bow = auto_trim_onset(load_48k_stereo(BOW_DIRECT), pre_ms=0.8)
    swish3 = widen_mono_subtle(auto_trim_onset(load_48k_stereo(SRC_CC0 / "swish_3.wav"), pre_ms=2.0), 0.60, 0.32)
    swish4 = widen_mono_subtle(auto_trim_onset(load_48k_stereo(SRC_CC0 / "swish_4.wav"), pre_ms=2.0), 0.60, 0.32)
    ballista = widen_mono_subtle(auto_trim_onset(load_48k_stereo(BALLISTA_TWANG), pre_ms=1.0), 0.50, 0.24)

    records: List[Dict[str, object]] = []

    # =========================================================================
    # V1: SONIC ARMOR PIERCER (1.15 s) — Crisp Warbow Snap + Supersonic Boom + Piercing Arrow Rip
    # =========================================================================
    b1 = np.zeros((2, int(round(1.15 * SR))), dtype=np.float64)
    # 1. Real CC0 taut bowstring snap + normal bow DNA (immediately recognizable as YOUR bow!)
    mix_at(b1, norm(slice_dur(cc0_bow, 0.42, speed=0.92, fade_in_ms=0.4, fade_out_ms=65.0)), 0.000, 0.62)
    mix_at(b1, norm(slice_dur(game_bow, 0.38, speed=0.90, fade_in_ms=0.4, fade_out_ms=55.0)), 0.000, 0.48)
    # 2. Explosive GPU heavy warbow crack & arrow launch (P1_02)
    mix_at(b1, norm(slice_dur(p1_02, 0.85, speed=1.00, fade_in_ms=0.3, fade_out_ms=120.0)), 0.000, 0.96)
    # 3. Supersonic air-barrier whip-crack (P2_01) right at 0 ms
    mix_at(b1, norm(hp(slice_dur(p2_01, 0.52, speed=1.02, fade_in_ms=0.2, fade_out_ms=90.0), 320.0)), 0.000, 0.84)
    # 4. Spiral supersonic air-tear wake (P2_02) rushing outward (+10 ms)
    mix_at(b1, norm(bp(slice_dur(p2_02, 0.96, speed=1.02, fade_in_ms=1.5, fade_out_ms=160.0), 160.0, 11500.0)), 0.010, 0.88)
    # 5. Deep seismic chest-thumping shockwave sub-boom (P3_03 + clean kinetic sub-punch!)
    mix_at(b1, norm(lp(slice_dur(p3_03, 0.72, speed=1.04, fade_in_ms=0.5, fade_out_ms=180.0), 260.0)), 0.000, 0.92)
    mix_at(b1, norm(synth_sub_punch(0.32, 165.0, 44.0, 0.038, 0.095)), 0.000, 0.62)
    # 6. Subtle piercing steel-arrowhead resonance ring (+6 ms — unmistakable piercing edge!)
    mix_at(b1, norm(bp(slice_dur(p4_03, 0.68, speed=1.08, fade_in_ms=2.0, fade_out_ms=180.0), 1400.0, 9500.0)), 0.006, 0.24)
    # 7. Crisp stereo fletching air-slice (swish_4)
    mix_at(b1, norm(hp(slice_dur(swish4, 0.36, speed=1.08, fade_in_ms=2.0, fade_out_ms=65.0), 650.0)), 0.018, 0.36)

    t1 = np.arange(b1.shape[1], dtype=np.float64) / SR
    b1 *= np.exp(-np.maximum(0.0, t1 - 0.30) / 0.36)[None, :]
    b1 = peak_eq(b1, 420.0, 850.0, -2.2)
    b1 = shelf_low(b1, 160.0, 2.5)
    b1 = shelf_high(b1, 3200.0, 1.8)
    v1 = master_impact(b1, target_rms100_db=-8.2, peak_db=-0.4, hp_hz=28.0, fade_in_ms=0.3, fade_out_ms=110.0)

    # =========================================================================
    # V2: THUNDER WARBOW SHOCKWAVE (1.30 s) — Maximum Heavy Greatbow Seismic Impact!
    # =========================================================================
    b2 = np.zeros((2, int(round(1.30 * SR))), dtype=np.float64)
    # 1. Heavy torsion greatbow & ballista string slam (B10 + P1_03 + cc0_bow pitched down for massive weight!)
    mix_at(b2, norm(slice_dur(cc0_bow, 0.45, speed=0.82, fade_in_ms=0.4, fade_out_ms=70.0)), 0.000, 0.65)
    mix_at(b2, norm(slice_dur(ballista, 0.72, speed=0.94, fade_in_ms=0.3, fade_out_ms=110.0)), 0.000, 0.78)
    mix_at(b2, norm(slice_dur(p1_03, 0.92, speed=0.95, fade_in_ms=0.4, fade_out_ms=140.0)), 0.000, 0.86)
    # 2. Violent air-shatter sonic boom (P2_01 + P2_02)
    mix_at(b2, norm(hp(slice_dur(p2_01, 0.48, speed=0.96, fade_in_ms=0.2, fade_out_ms=90.0), 380.0)), 0.000, 0.72)
    mix_at(b2, norm(bp(slice_dur(p2_02, 1.10, speed=0.94, fade_in_ms=1.5, fade_out_ms=180.0), 120.0, 9500.0)), 0.008, 0.92)
    # 3. FULL-WEIGHT seismic pressure-wave blast (P3_03 + P3_01 + deep sub drop!)
    mix_at(b2, norm(lp(slice_dur(p3_03, 0.98, speed=0.92, fade_in_ms=0.4, fade_out_ms=220.0), 280.0)), 0.000, 1.25)
    mix_at(b2, norm(lp(slice_dur(p3_01, 0.88, speed=0.96, fade_in_ms=1.0, fade_out_ms=180.0), 420.0)), 0.004, 0.65)
    mix_at(b2, norm(synth_sub_punch(0.44, 148.0, 36.0, 0.048, 0.135)), 0.000, 0.85)
    # 4. Subtle steel tension ring + heavy wind wake
    mix_at(b2, norm(bp(slice_dur(p4_03, 0.72, speed=0.96, fade_in_ms=2.0, fade_out_ms=200.0), 1200.0, 8200.0)), 0.008, 0.18)
    mix_at(b2, norm(bp(slice_dur(swish3, 0.42, speed=0.92, fade_in_ms=2.0, fade_out_ms=80.0), 350.0, 6500.0)), 0.015, 0.34)

    t2 = np.arange(b2.shape[1], dtype=np.float64) / SR
    b2 *= np.exp(-np.maximum(0.0, t2 - 0.36) / 0.42)[None, :]
    b2 = peak_eq(b2, 420.0, 820.0, -2.5)
    b2 = shelf_low(b2, 150.0, 4.0)
    b2 = shelf_high(b2, 3000.0, 1.2)
    v2 = master_impact(b2, target_rms100_db=-7.4, peak_db=-0.3, hp_hz=26.0, fade_in_ms=0.3, fade_out_ms=130.0)

    # =========================================================================
    # V3: DRAGON PIERCER RAZOR WIND (1.20 s) — Blinding Speed, Razor Vortex & Piercing Snap!
    # =========================================================================
    b3 = np.zeros((2, int(round(1.20 * SR))), dtype=np.float64)
    # 1. Razor-crisp taut warbow release (P1_02 + English_Longbow + game_bow)
    mix_at(b3, norm(slice_dur(cc0_longbow, 0.40, speed=1.06, fade_in_ms=0.3, fade_out_ms=65.0)), 0.000, 0.56)
    mix_at(b3, norm(slice_dur(game_bow, 0.35, speed=1.02, fade_in_ms=0.3, fade_out_ms=50.0)), 0.000, 0.50)
    mix_at(b3, norm(slice_dur(p1_02, 0.88, speed=1.06, fade_in_ms=0.25, fade_out_ms=110.0)), 0.000, 1.00)
    # 2. Intense high-velocity supersonic crack & piercing wind vortex (P2_01 + P2_02 + swish_4!)
    mix_at(b3, norm(hp(slice_dur(p2_01, 0.58, speed=1.08, fade_in_ms=0.2, fade_out_ms=95.0), 420.0)), 0.000, 0.96)
    mix_at(b3, norm(hp(slice_dur(p2_02, 1.04, speed=1.08, fade_in_ms=1.0, fade_out_ms=160.0), 220.0)), 0.008, 1.02)
    mix_at(b3, norm(hp(slice_dur(swish4, 0.42, speed=1.12, fade_in_ms=1.5, fade_out_ms=75.0), 800.0)), 0.014, 0.52)
    # 3. Metallic razor-blade/steel-arrow piercing shriek accent (P4_03)
    mix_at(b3, norm(bp(slice_dur(p4_03, 0.78, speed=1.14, fade_in_ms=1.5, fade_out_ms=190.0), 1600.0, 11000.0)), 0.004, 0.36)
    # 4. Tight, punchy kinetic chest kick (no long mud, pure snap!)
    mix_at(b3, norm(lp(slice_dur(p3_03, 0.48, speed=1.12, fade_in_ms=0.4, fade_out_ms=120.0), 240.0)), 0.000, 0.78)
    mix_at(b3, norm(synth_sub_punch(0.26, 185.0, 48.0, 0.032, 0.078)), 0.000, 0.64)

    t3 = np.arange(b3.shape[1], dtype=np.float64) / SR
    b3 *= np.exp(-np.maximum(0.0, t3 - 0.28) / 0.38)[None, :]
    b3 = peak_eq(b3, 450.0, 900.0, -2.4)
    b3 = shelf_low(b3, 170.0, 1.8)
    b3 = shelf_high(b3, 3000.0, 2.8)
    v3 = master_impact(b3, target_rms100_db=-8.5, peak_db=-0.4, hp_hz=30.0, fade_in_ms=0.25, fade_out_ms=115.0)

    # Save singles + 2x comparison previews (Normal Bow -> 0.5s -> HeartPiercingArrow -> 0.7s -> HeartPiercingArrow!)
    # Putting 1 normal bow shot first in each preview makes the impact contrast IMMEDIATELY visceral!
    norm_ref = norm(slice_dur(game_bow, 0.43, speed=1.0, fade_in_ms=0.5, fade_out_ms=25.0), peak=10.0 ** (-5.1 / 20.0))

    specs = [
        ("V1_SonicArmorPiercer", v1, "PREVIEW_1_HeartPiercing_V1_SonicArmorPiercer.wav"),
        ("V2_ThunderWarbow_Shockwave", v2, "PREVIEW_2_HeartPiercing_V2_ThunderWarbow_Shockwave.wav"),
        ("V3_DragonPiercer_RazorWind", v3, "PREVIEW_3_HeartPiercing_V3_DragonPiercer_RazorWind.wav"),
    ]
    for tag, clip, prev_name in specs:
        r_single = write_wav_24bit(OUT / tag / "S_HeartPiercingArrow_Release.wav", clip)
        records.append(r_single)
        # Audition reel: 2 clean isolated shots (0.00 s & +1.85 s) — zero confusion, pure candidate focus!
        dur = clip.shape[1] / SR
        prev = np.zeros((2, int(round((dur * 2 + 0.75) * SR))), dtype=np.float64)
        mix_at(prev, clip, 0.00, 1.0)
        mix_at(prev, clip, dur + 0.75, 1.0)
        records.append(write_wav_24bit(OUT / prev_name, prev))

    # Also write an A/B contrast preview: Normal Bow -> Old Weak V4 -> New V1 / V2 / V3
    old_v4 = load_48k_stereo(SKILL_ROOT / "SelectedH/S_HeartPiercingArrow_Release.wav")
    ab = np.zeros((2, int(round(6.6 * SR))), dtype=np.float64)
    mix_at(ab, norm_ref, 0.00, 0.60)
    mix_at(ab, old_v4, 0.90, 0.60)
    mix_at(ab, v1, 2.20, 0.95)
    mix_at(ab, v2, 3.70, 0.95)
    mix_at(ab, v3, 5.25, 0.95)
    records.append(write_wav_24bit(OUT / "PREVIEW_0_AB_Normal_OldV4_vs_New_V1_V2_V3.wav", ab))

    manifest = {
        "batch": "HeartPiercingArrow_ColabImpactV2_20261126",
        "sources": [
            "Colab L4 MMAudio large_44k_v2 bespoke stems (P1_SonicBowCrack, P2_SupersonicAirTear, P3_ShockwaveSubBoom, P4_SteelTensionTwang)",
            "CC0 1.0 real recorded bow/arrow stems (Bow.wav, English_Longbow_Shoot.wav, swish_3.wav, swish_4.wav)",
            "Project S_BowVideoDirect_Release.wav & B10_BallistaTwangBolt_01",
        ],
        "output_format": "48 kHz / 24-bit True Stereo PCM",
        "files": records,
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

    print("\n=== HEART-PIERCING ARROW HIGH-IMPACT CANDIDATES (48 kHz / 24-bit Stereo) ===")
    print(f"{'File':56s} {'Dur':>5s} {'Pk':>6s} {'RMS':>6s} {'R100':>6s} {'Sub%':>5s} {'Lo%':>5s} {'Mid%':>5s} {'Hi%':>5s} {'Lead':>5s}")
    for rec in records:
        print(
            f"{rec['file']:56s} {rec['duration_s']:5.2f} {rec['peak_dbfs']:6.1f} {rec['rms_dbfs']:6.1f} "
            f"{rec['rms100_dbfs']:6.1f} {rec['sub_pct']:5.1f} {rec['lo_pct']:5.1f} {rec['mid_pct']:5.1f} {rec['hi_pct']:5.1f} {rec['lead_ms']:5.1f}"
        )


if __name__ == "__main__":
    main()
