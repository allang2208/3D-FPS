"""Compose 100% real-recorded 192 kHz -> 48 kHz / 24-bit True Stereo CC0 audio suite for SVCh (7.62x54mmR DMR).

Source library: The Free Firearm Sound Library (CC0 1.0 Universal Public Domain, 192 kHz / 24-bit True Stereo):
  - Mosin Nagant (literal 7.62x54mmR behind-shooter, near, mid, far outdoor gunshots)
  - Tikka Model T3 (.30-06 modern precision sniper behind-shooter, near, mid gunshots & detachable sniper mag/bolt)
  - SKS (Russian 7.62 semi-auto gas-piston action & straight-pull loaded slide rack)
  - Savage 10 .300 Blackout (real suppressed .30-caliber sniper behind-shooter, near, muzzle baffle & mid outdoor)
  - AK-47 & AR-15 (Russian rock-and-lock steel magazine + modern aluminum/steel upper-receiver handling)

Exact SVCh runtime contracts verified from SVCHWeaponAssets.h & SVDCompletion20260923/authoring.json:
  - Fire         : 4-variant rotating bank (S_SVCH_Fire_01..04), semi-auto 0.30 s interval
  - Suppressed   : 4-variant rotating bank (S_SVCh_Suppressed_01..04), semi-auto 0.30 s interval
  - Equip        : A_SVD_equip = 1.70 s -> 0.000 s EquipRaise, 0.533 s (64/120) ChargePull, 0.833 s (100/120) ChargeRelease
  - Tactical Rel : A_SVD_reload = 3.333 s -> 0.433 s MagOut, 1.833 s MagInsert, 2.000 s MagSeat
  - Empty Reload : A_SVD_reload_empty = 4.292 s -> 0.433 / 1.833 / 2.000 s + 2.583 s (310/120) ChargePull, 2.917 s (350/120) ChargeRelease
"""

from __future__ import annotations

import hashlib
import json
import math
import wave
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

import numpy as np
import soundfile as sf
from scipy import signal

SR = 48000
ROOT = Path(r"D:\FPS3D\FPSGAME\SourceAssets\SVCHReplacement20261018\AudioRealCC0_20261126")
RAW = ROOT / "RawCC0"
OUT = ROOT / "ComposedCandidates"

_CACHE: Dict[str, np.ndarray] = {}


def load_cc0(rel: str) -> np.ndarray:
    if rel in _CACHE:
        return _CACHE[rel]
    x, src_sr = sf.read(str(RAW / rel), always_2d=True, dtype="float64")
    x = np.repeat(x, 2, axis=1) if x.shape[1] == 1 else x[:, :2]
    x = x.T
    x = x - np.mean(x, axis=1, keepdims=True)
    if src_sr != SR:
        g = math.gcd(src_sr, SR)
        x = signal.resample_poly(x, SR // g, src_sr // g, axis=1)
    _CACHE[rel] = x
    return x


def pitch_speed(x: np.ndarray, ratio: float) -> np.ndarray:
    if abs(ratio - 1.0) < 1e-4:
        return x.copy()
    up = int(round(1000 / ratio))
    down = 1000
    g = math.gcd(up, down)
    return signal.resample_poly(x, up // g, down // g, axis=1)


def cut(rel: str, start_s: float, dur_s: float, speed: float = 1.0, fade_in_ms: float = 0.5, fade_out_ms: float = 20.0) -> np.ndarray:
    x = load_cc0(rel)
    i0 = max(0, int(round(start_s * SR)))
    n_src = max(16, int(round(dur_s * speed * SR)))
    seg = x[:, i0 : i0 + n_src].copy()
    if seg.shape[1] < n_src:
        seg = np.pad(seg, ((0, 0), (0, n_src - seg.shape[1])))
    if abs(speed - 1.0) > 1e-4:
        seg = pitch_speed(seg, speed)
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


def center_stereo(x: np.ndarray, width: float = 0.68) -> np.ndarray:
    mid = 0.5 * (x[0] + x[1])
    side = 0.5 * (x[0] - x[1]) * width
    return np.stack([mid + side, mid - side], axis=0)


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


def master_fire_sniper(
    x: np.ndarray,
    target_rms80_db: float = -10.3,
    peak_db: float = -0.6,
    hp_hz: float = 34.0,
    width: float = 0.68,
    fade_in_ms: float = 0.25,
    fade_out_ms: float = 75.0,
) -> np.ndarray:
    x = x - np.mean(x, axis=1, keepdims=True)
    x = hp(x, hp_hz, order=2)
    x = center_stereo(x, width)

    ceil = 10.0 ** (peak_db / 20.0)
    knee = 0.42 * ceil
    head = ceil - knee

    mono0 = x.mean(axis=0)
    cur_rms80 = float(np.sqrt(np.mean(mono0[: min(len(mono0), int(0.08 * SR))] ** 2)) + 1e-12)
    tgt_lin = 10.0 ** (target_rms80_db / 20.0)
    drive = tgt_lin / cur_rms80
    for _ in range(4):
        y = x * drive
        mag = np.max(np.abs(y), axis=0)
        over = np.maximum(0.0, mag - knee)
        mapped = knee + head * np.tanh(over / head)
        gain = np.where(mag > knee, mapped / np.maximum(mag, 1e-12), 1.0)
        y = y * gain[None, :]
        m = y.mean(axis=0)
        r80 = float(np.sqrt(np.mean(m[: min(len(m), int(0.08 * SR))] ** 2)) + 1e-12)
        drive *= (tgt_lin / r80) ** 0.75
    x = hp(y, hp_hz, order=2)
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


def master_foley(x: np.ndarray, peak_db: float = -2.2, hp_hz: float = 55.0, width: float = 0.52, comp_db: float = 5.2, fi_ms: float = 1.0, fo_ms: float = 28.0) -> np.ndarray:
    x = x - np.mean(x, axis=1, keepdims=True)
    x = hp(x, hp_hz, order=2)
    x = center_stereo(x, width)
    pk = float(np.max(np.abs(x)) + 1e-12)
    ceil = 10.0 ** (peak_db / 20.0)
    boost = 10.0 ** (comp_db / 20.0)
    x = x * (ceil * boost / pk)
    knee = 0.52 * ceil
    head = ceil - knee
    mag = np.max(np.abs(x), axis=0)
    over = np.maximum(0.0, mag - knee)
    mapped = knee + head * (over / (over + head))
    gain = np.where(mag > knee, mapped / np.maximum(mag, 1e-12), 1.0)
    x = x * gain[None, :]
    pk2 = float(np.max(np.abs(x)) + 1e-12)
    if pk2 > ceil:
        x *= ceil / pk2
    fi = min(x.shape[1] // 4, int(round(fi_ms * 0.001 * SR)))
    fo = min(x.shape[1] // 3, int(round(fo_ms * 0.001 * SR)))
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
    rms80 = float(np.sqrt(np.mean(mono[: min(len(mono), int(0.08 * SR))] ** 2)) + 1e-12)
    seg = mono[: min(len(mono), int(0.14 * SR))]
    fft = np.abs(np.fft.rfft(seg)) ** 2
    fr = np.fft.rfftfreq(len(seg), 1.0 / SR)
    tot = float(fft.sum()) + 1e-12
    lo = 100.0 * float(fft[(fr >= 40) & (fr < 300)].sum()) / tot
    mid = 100.0 * float(fft[(fr >= 300) & (fr < 2500)].sum()) / tot
    hi = 100.0 * float(fft[(fr >= 2500) & (fr < 14000)].sum()) / tot
    sha = hashlib.sha256(path.read_bytes()).hexdigest()[:16]
    return {
        "file": str(path.relative_to(OUT)).replace("\\", "/"),
        "duration_s": round(data.shape[1] / SR, 3),
        "peak_dbfs": round(20.0 * math.log10(pk), 2),
        "rms_dbfs": round(20.0 * math.log10(rms), 2),
        "rms80_dbfs": round(20.0 * math.log10(rms80), 2),
        "lo_pct": round(lo, 1),
        "mid_pct": round(mid, 1),
        "hi_pct": round(hi, 1),
        "sha256_16": sha,
    }


def render_dmr_fire_preview(variants: List[np.ndarray], interval_s: float = 0.30) -> np.ndarray:
    """1 isolated precision sniper shot -> 2-round rapid double-tap -> 4-round DMR cadence @ 0.30 s!"""
    total_s = 4.65
    out = np.zeros((2, int(round(total_s * SR))), dtype=np.float64)
    schedule = [
        (0.00, 0),
        (1.30, 1),
        (1.30 + interval_s, 2),
        (2.65, 3),
        (2.65 + interval_s, 0),
        (2.65 + 2 * interval_s, 2),
        (2.65 + 3 * interval_s, 1),
    ]
    for t_s, idx in schedule:
        mix_at(out, variants[idx], t_s, 0.88)
    pk = float(np.max(np.abs(out)) + 1e-12)
    ceil = 10.0 ** (-0.5 / 20.0)
    if pk > ceil:
        out *= ceil / pk
    return out


def render_timeline(total_s: float, events: Sequence[Tuple[float, np.ndarray, float]]) -> np.ndarray:
    out = np.zeros((2, int(round(total_s * SR))), dtype=np.float64)
    for t_s, clip, gain in events:
        mix_at(out, clip, t_s, gain)
    pk = float(np.max(np.abs(out)) + 1e-12)
    ceil = 10.0 ** (-0.8 / 20.0)
    if pk > ceil:
        out *= ceil / pk
    return out


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    records: List[Dict[str, object]] = []

    # =========================================================================
    # 1. UNSUPPRESSED SVCh 7.62x54mmR SEMI-AUTO DMR FIRE (2 Styles x 4 Variants)
    # =========================================================================
    # Literal 7.62x54mmR behind-shooter takes (Mosin M_20 & M_22)
    mosin_behind = [
        ("Mosin_Nagant/M_20.wav", 1.833),
        ("Mosin_Nagant/M_20.wav", 10.603),
        ("Mosin_Nagant/M_22.wav", 1.178),
        ("Mosin_Nagant/M_22.wav", 8.253),
    ]
    # Literal 7.62x54mmR near-distance explosive crack (Mosin M_19 & M_21)
    mosin_near = [
        ("Mosin_Nagant/M_19.wav", 2.373),
        ("Mosin_Nagant/M_19.wav", 11.148),
        ("Mosin_Nagant/M_21.wav", 1.028),
        ("Mosin_Nagant/M_21.wav", 8.103),
    ]
    # Literal 7.62x54mmR rolling outdoor mid/far canyon tail (Mosin M_24, M_26, M_23)
    mosin_tail = [
        ("Mosin_Nagant/M_24.wav", 0.798),
        ("Mosin_Nagant/M_26.wav", 2.103),
        ("Mosin_Nagant/M_24.wav", 9.713),
        ("Mosin_Nagant/M_26.wav", 10.393),
    ]
    mosin_far = [
        ("Mosin_Nagant/M_23.wav", 0.998),
        ("Mosin_Nagant/M_23.wav", 9.913),
        ("Mosin_Nagant/M_23.wav", 18.668),
        ("Mosin_Nagant/M_26.wav", 20.123),
    ]
    # Modern precision .30-06 sniper behind-shooter + near whip-crack (Tikka W_26..W_29)
    tikka_behind = [
        ("Tikka/W_26.wav", 0.848),
        ("Tikka/W_26.wav", 8.938),
        ("Tikka/W_28.wav", 0.723),
        ("Tikka/W_28.wav", 11.678),
    ]
    tikka_near = [
        ("Tikka/W_27.wav", 0.738),
        ("Tikka/W_27.wav", 8.828),
        ("Tikka/W_29.wav", 0.573),
        ("Tikka/W_29.wav", 11.528),
    ]
    # Russian 7.62 semi-auto gas-piston bolt cycling snap (+14 ms behind blast!)
    piston_snaps = [
        ("SKS/U_4.wav", 1.738),
        ("AK-47/C_1.wav", 0.302),
        ("SKS/U_5.wav", 1.292),
        ("AK-47/C_13.wav", 0.178),
    ]

    def compose_svch_fire(heavy_thunder: bool) -> List[np.ndarray]:
        bank: List[np.ndarray] = []
        dur = 1.06 if heavy_thunder else 0.96
        for i in range(4):
            buf = np.zeros((2, int(round(dur * SR))), dtype=np.float64)

            # 1. Primary literal 7.62x54mmR behind-shooter blast (Mosin M_20/M_22)
            mb_f, mb_t = mosin_behind[i]
            mb = norm(cut(mb_f, mb_t, dur, speed=0.95 if heavy_thunder else 1.00, fade_in_ms=0.2, fade_out_ms=110.0))
            mix_at(buf, mb, 0.000, 1.00)

            # 2. Modern precision free-floating sniper barrel punch (Tikka .30-06 W_26/W_28)
            tb_f, tb_t = tikka_behind[i]
            tb = norm(cut(tb_f, tb_t, 0.72, speed=0.96 if heavy_thunder else 1.02, fade_in_ms=0.2, fade_out_ms=95.0))
            mix_at(buf, tb, 0.000, 0.65 if not heavy_thunder else 0.78)

            # 3. Blistering 7.62x54R + .30-06 supersonic muzzle whip-crack (0..180 ms)
            mn_f, mn_t = mosin_near[i]
            mn = norm(cut(mn_f, mn_t, 0.32, speed=0.98 if heavy_thunder else 1.02, fade_in_ms=0.2, fade_out_ms=65.0))
            tn_f, tn_t = tikka_near[i]
            tn = norm(cut(tn_f, tn_t, 0.28, speed=1.00, fade_in_ms=0.2, fade_out_ms=60.0))
            mix_at(buf, hp(mn, 1100.0), 0.000, 0.44 if not heavy_thunder else 0.38)
            mix_at(buf, hp(tn, 1800.0), 0.000, 0.38 if not heavy_thunder else 0.30)

            # 4. Authentic rolling 7.62x54R outdoor valley echo tail (+22 ms & +45 ms)
            mt_f, mt_t = mosin_tail[i]
            mt = norm(cut(mt_f, mt_t, dur - 0.02, speed=0.96 if heavy_thunder else 1.00, fade_in_ms=8.0, fade_out_ms=140.0))
            mix_at(buf, bp(mt, 120.0, 5800.0), 0.022, 0.46 if not heavy_thunder else 0.62)

            if heavy_thunder:
                mf_f, mf_t = mosin_far[i]
                mf = norm(cut(mf_f, mf_t, dur - 0.04, speed=0.92, fade_in_ms=18.0, fade_out_ms=160.0))
                mix_at(buf, bp(mf, 90.0, 3800.0), 0.042, 0.52)

            # 5. Unmistakable Russian 7.62 semi-auto short-stroke gas-piston metallic bolt snap (+15 ms)
            ps_f, ps_t = piston_snaps[i]
            ps = norm(cut(ps_f, ps_t, 0.11, speed=1.02, fade_in_ms=0.5, fade_out_ms=28.0))
            mix_at(buf, bp(ps, 1200.0, 9500.0), 0.015 + 0.001 * i, 0.24 if not heavy_thunder else 0.20)

            # Natural sniper tail shaping (full explosive roar, smooth decay into clean silence)
            t = np.arange(buf.shape[1], dtype=np.float64) / SR
            dt = np.maximum(0.0, t - (0.14 if heavy_thunder else 0.11))
            tau = 0.36 if heavy_thunder else 0.28
            buf *= np.exp(-((dt / tau) ** 1.15))[None, :]

            # Anti-boxy surgical polish: scoop 450-850 Hz mud, lift deep sniper chest punch + supersonic crack!
            buf = peak_eq(buf, 440.0, 880.0, -2.8)
            if heavy_thunder:
                buf = shelf_low(buf, 200.0, 6.0)
                buf = shelf_high(buf, 3000.0, 1.8)
            else:
                buf = shelf_low(buf, 220.0, 2.8)
                buf = shelf_high(buf, 2800.0, 2.6)

            bank.append(
                master_fire_sniper(
                    buf,
                    target_rms80_db=-9.6 if heavy_thunder else -10.4,
                    peak_db=-0.5 if heavy_thunder else -0.6,
                    hp_hz=34.0,
                    width=0.68,
                    fade_in_ms=0.25,
                    fade_out_ms=95.0,
                )
            )
        return bank

    for tag, ht, prev_name in [
        ("V1_Real762x54R_PrecisionDMR", False, "PREVIEW_1_SVCH_Fire_V1_Real762x54R_PrecisionDMR.wav"),
        ("V2_HeavySniper_ThunderDMR", True, "PREVIEW_2_SVCH_Fire_V2_HeavySniper_ThunderDMR.wav"),
    ]:
        d = OUT / f"Fire_{tag}"
        bank = compose_svch_fire(ht)
        for idx, clip in enumerate(bank, start=1):
            records.append(write_wav_24bit(d / f"S_SVCH_Fire_{idx:02d}.wav", clip))
        records.append(write_wav_24bit(OUT / prev_name, render_dmr_fire_preview(bank, 0.30)))

    # =========================================================================
    # 2. SUPPRESSED SVCh 7.62x54mmR DMR FIRE (2 Styles x 4 Variants)
    # =========================================================================
    sup_behind = [
        ("Savage_10__300_Blackout/T_28.wav", 0.683),
        ("Savage_10__300_Blackout/T_28.wav", 3.503),
        ("Savage_10__300_Blackout/T_30.wav", 0.748),
        ("Savage_10__300_Blackout/T_30.wav", 3.293),
    ]
    sup_near = [
        ("Savage_10__300_Blackout/T_29.wav", 0.623),
        ("Savage_10__300_Blackout/T_29.wav", 3.353),
        ("Savage_10__300_Blackout/T_31.wav", 1.333),
        ("Savage_10__300_Blackout/T_31.wav", 5.883),
    ]
    sup_muzzle = [
        ("Savage_10__300_Blackout/T_15.wav", 6.398),
        ("Savage_10__300_Blackout/T_15.wav", 11.583),
        ("Savage_10__300_Blackout/T_15.wav", 14.378),
        ("Savage_10__300_Blackout/T_15.wav", 11.583),
    ]
    sup_mid = [
        ("Savage_10__300_Blackout/T_20.wav", 1.028),
        ("Savage_10__300_Blackout/T_20.wav", 4.473),
        ("Savage_10__300_Blackout/T_22.wav", 0.988),
        ("Savage_10__300_Blackout/T_22.wav", 4.418),
    ]
    # Real .30-cal unsuppressed micro-crack for titanium 7.62x54R supersonic whip accent
    sup_crack = [
        ("Savage_10__300_Blackout/T_24.wav", 1.303),
        ("Savage_10__300_Blackout/T_24.wav", 6.718),
        ("Savage_10__300_Blackout/T_26.wav", 1.058),
        ("Savage_10__300_Blackout/T_26.wav", 5.288),
    ]

    def compose_svch_suppressed(deep_assassin: bool) -> List[np.ndarray]:
        bank: List[np.ndarray] = []
        dur = 0.72 if deep_assassin else 0.66
        for i in range(4):
            buf = np.zeros((2, int(round(dur * SR))), dtype=np.float64)

            # 1. REAL 7.62x54mmR + .30-06 pressurized suppressor chamber thump (baffle-muffled real full-power rifle!)
            # Gives unmistakable heavy 7.62x54R suppressed weight (Lo 38-52%) instead of a thin airgun click!
            mb_f, mb_t = mosin_behind[i]
            mb_raw = norm(cut(mb_f, mb_t, 0.56, speed=0.88 if deep_assassin else 0.94, fade_in_ms=0.3, fade_out_ms=95.0))
            tb_f, tb_t = tikka_behind[i]
            tb_raw = norm(cut(tb_f, tb_t, 0.50, speed=0.90 if deep_assassin else 0.96, fade_in_ms=0.3, fade_out_ms=85.0))
            mix_at(buf, norm(lp(mb_raw, 420.0 if deep_assassin else 620.0, order=2)), 0.000, 1.05 if deep_assassin else 0.85)
            mix_at(buf, norm(lp(tb_raw, 550.0 if deep_assassin else 950.0, order=2)), 0.000, 0.65 if deep_assassin else 0.72)

            # 2. REAL .30-cal suppressed sniper behind-shooter + near-mic baffle body (LP cleanly so zero shrill hiss!)
            sb_f, sb_t = sup_behind[i]
            sb = norm(cut(sb_f, sb_t, dur, speed=0.86 if deep_assassin else 0.94, fade_in_ms=0.3, fade_out_ms=85.0))
            mix_at(buf, lp(sb, 3200.0 if deep_assassin else 4600.0), 0.000, 0.58 if deep_assassin else 0.76)

            sn_f, sn_t = sup_near[i]
            sn = norm(cut(sn_f, sn_t, 0.42, speed=0.88 if deep_assassin else 0.94, fade_in_ms=0.3, fade_out_ms=70.0))
            mix_at(buf, bp(sn, 180.0, 2600.0 if deep_assassin else 3600.0), 0.000, 0.52 if deep_assassin else 0.58)

            # 3. Tight titanium suppressor gas puff (T_15 indoor muzzle baffle — crisp air-release, restrained!)
            sm_f, sm_t = sup_muzzle[i]
            sm = norm(cut(sm_f, sm_t, 0.24, speed=0.92 if deep_assassin else 1.00, fade_in_ms=0.3, fade_out_ms=55.0))
            mix_at(buf, bp(sm, 400.0, 5200.0), 0.000, 0.24 if deep_assassin else 0.34)

            # 4. Subtle outdoor suppressed air tail (T_20/T_22 mid-distance suppressed!)
            sd_f, sd_t = sup_mid[i]
            sd = norm(cut(sd_f, sd_t, dur - 0.015, speed=0.90 if deep_assassin else 0.96, fade_in_ms=6.0, fade_out_ms=95.0))
            mix_at(buf, bp(sd, 140.0, 2800.0), 0.015, 0.34 if deep_assassin else 0.38)

            # 5. Restrained, tactile SVCh semi-auto steel bolt cycle (+14 ms — mechanical accent, NEVER overpowering!)
            ps_f, ps_t = piston_snaps[i]
            ps = norm(cut(ps_f, ps_t, 0.095, speed=0.98 if deep_assassin else 1.04, fade_in_ms=0.5, fade_out_ms=26.0))
            mix_at(buf, bp(ps, 900.0, 6200.0), 0.014 + 0.001 * i, 0.16 if deep_assassin else 0.22)

            # Clean pressurized decay envelope
            t = np.arange(buf.shape[1], dtype=np.float64) / SR
            dt = np.maximum(0.0, t - (0.095 if deep_assassin else 0.080))
            tau = 0.20 if deep_assassin else 0.165
            buf *= np.exp(-((dt / tau) ** 1.15))[None, :]

            if deep_assassin:
                buf = shelf_low(buf, 220.0, 3.2)
                buf = lp(buf, 4800.0, order=2)
            else:
                buf = shelf_low(buf, 220.0, 1.8)
                buf = lp(buf, 6800.0, order=2)

            bank.append(
                master_fire_sniper(
                    buf,
                    target_rms80_db=-14.2 if deep_assassin else -15.0,
                    peak_db=-1.2 if deep_assassin else -1.5,
                    hp_hz=42.0,
                    width=0.58,
                    fade_in_ms=0.25,
                    fade_out_ms=65.0,
                )
            )
        return bank

    for tag, da, prev_name in [
        ("V1_TacticalTitanium_Crisp", False, "PREVIEW_3_SVCH_Suppressed_V1_TacticalTitanium_Crisp.wav"),
        ("V2_DeepSubsonic_Assassin", True, "PREVIEW_4_SVCH_Suppressed_V2_DeepSubsonic_Assassin.wav"),
    ]:
        d = OUT / f"Suppressed_{tag}"
        bank = compose_svch_suppressed(da)
        for idx, clip in enumerate(bank, start=1):
            records.append(write_wav_24bit(d / f"S_SVCh_Suppressed_{idx:02d}.wav", clip))
        records.append(write_wav_24bit(OUT / prev_name, render_dmr_fire_preview(bank, 0.30)))

    # =========================================================================
    # 3. SVCh EQUIP & RELOAD MECHANICAL SUITE (6 Dedicated Cues x 2 Styles)
    # =========================================================================
    # Exact 120 fps animation clocks:
    #   Equip (1.70 s): 0.000 s EquipRaise -> 0.533 s ChargePull -> 0.833 s ChargeRelease
    #   Reload (3.33 s): 0.433 s MagOut -> 1.833 s MagInsert -> 2.000 s MagSeat
    #   Empty  (4.29 s): 0.433 / 1.833 / 2.000 s + 2.583 s ChargePull -> 2.917 s ChargeRelease
    def compose_svch_mechanics(heavy_russian: bool) -> Dict[str, np.ndarray]:
        sp = 0.92 if heavy_russian else 1.00
        lb = 2.6 if heavy_russian else 1.0
        hb = 0.6 if heavy_russian else 1.6
        cues: Dict[str, np.ndarray] = {}

        def fin(buf: np.ndarray, pk_db: float = -2.2, hp_hz: float = 55.0, comp_db: float = 5.2, fi_ms: float = 1.0, fo_ms: float = 28.0) -> np.ndarray:
            buf = shelf_low(buf, 260.0, lb)
            buf = shelf_high(buf, 3200.0, hb)
            return master_foley(buf, peak_db=pk_db, hp_hz=hp_hz, width=0.52, comp_db=comp_db, fi_ms=fi_ms, fo_ms=fo_ms)

        # 1. EquipRaise (0.52 s @ t=0.000 s): Precision DMR sling/stock hoist + aluminum/steel receiver lift + left hand grip contact leading cleanly into ChargePull @ 0.533 s!
        b = np.zeros((2, int(round(0.52 * SR))), dtype=np.float64)
        lift = norm(cut("AR-15/D_17.wav", 3.60, 0.34, speed=sp * 0.94, fade_in_ms=14.0, fade_out_ms=65.0))
        mix_at(b, lp(lift, 2800.0), 0.005, 0.68)
        # Subtle rigid precision sniper chassis/sling metal shift
        chassis = norm(cut("Tikka/W_2.wav", 1.050, 0.16, speed=sp * 0.90, fade_in_ms=8.0, fade_out_ms=48.0))
        mix_at(b, bp(chassis, 240.0, 3200.0), 0.120, 0.36 if not heavy_russian else 0.48)
        # Tactile gloved hand reach onto left charging handle / handguard (~0.32 s)
        grip = norm(cut("AR-15/D_18.wav", 1.832, 0.18, speed=sp * 0.96, fade_in_ms=6.0, fade_out_ms=48.0))
        mix_at(b, bp(grip, 160.0, 3800.0), 0.300, 0.72)
        cues["S_SVCH_EquipRaise"] = fin(b, pk_db=-4.2, hp_hz=65.0, comp_db=4.4, fi_ms=10.0, fo_ms=45.0)

        # 2. MagOut (0.38 s @ t=0.433 s): Crisp paddle-latch press + 10-rd 7.62x54R heavy steel mag rock-out!
        b = np.zeros((2, int(round(0.38 * SR))), dtype=np.float64)
        # Paddle release click right at t=0
        latch = norm(cut("AR-15/D_20.wav", 0.355, 0.10, speed=sp * 0.96, fade_in_ms=0.8, fade_out_ms=25.0))
        mix_at(b, hp(latch, 500.0), 0.000, 0.52)
        # Loaded precision sniper box mag detach (Tikka W_5) + Russian steel rock-out (AK C_11)
        tik_out = norm(cut("Tikka/W_5.wav", 1.060, 0.28, speed=sp * 0.96, fade_in_ms=1.0, fade_out_ms=45.0))
        ak_out = norm(cut("AK-47/C_11.wav", 0.280, 0.30, speed=sp * 0.94, fade_in_ms=1.0, fade_out_ms=48.0))
        mix_at(b, tik_out, 0.015, 0.88 if not heavy_russian else 0.65)
        mix_at(b, ak_out, 0.025, 0.68 if not heavy_russian else 1.00)
        cues["S_SVCH_MagOut"] = fin(b, pk_db=-2.8, hp_hz=65.0)

        # 3. MagInsert (0.22 s @ t=1.833 s): Front steel lug hooking & guiding into rigid SVCh monolithic magwell (167 ms before MagSeat!)
        b = np.zeros((2, int(round(0.22 * SR))), dtype=np.float64)
        tik_in = norm(cut("Tikka/W_2.wav", 1.055, 0.19, speed=sp * 1.02, fade_in_ms=1.0, fade_out_ms=35.0))
        ar_in = norm(cut("AR-15/D_4.wav", 0.935, 0.18, speed=sp * 1.04, fade_in_ms=1.0, fade_out_ms=35.0))
        mix_at(b, tik_in, 0.000, 0.90)
        mix_at(b, bp(ar_in, 400.0, 7500.0), 0.012, 0.62 if not heavy_russian else 0.48)
        if heavy_russian:
            ak_guide = norm(cut("AK-47/C_10.wav", 0.275, 0.16, speed=0.98, fade_in_ms=1.5, fade_out_ms=38.0))
            mix_at(b, bp(ak_guide, 200.0, 4800.0), 0.005, 0.55)
        cues["S_SVCH_MagInsert"] = fin(b, pk_db=-3.6, hp_hz=85.0, fo_ms=32.0)

        # 4. MagSeat (0.34 s @ t=2.000 s): Authoritative rock-and-lock heavy steel 7.62x54R mag latch click & solid palm tap!
        b = np.zeros((2, int(round(0.34 * SR))), dtype=np.float64)
        ak_seat = norm(cut("AK-47/C_10.wav", 0.295, 0.26, speed=sp * 0.94, fade_in_ms=0.6, fade_out_ms=42.0))
        tik_seat = norm(cut("Tikka/W_4.wav", 0.978, 0.24, speed=sp * 0.96, fade_in_ms=0.6, fade_out_ms=40.0))
        click = norm(cut("AR-15/D_19.wav", 0.315, 0.12, speed=sp * 0.95, fade_in_ms=0.5, fade_out_ms=26.0))
        mix_at(b, ak_seat, 0.000, 0.85 if not heavy_russian else 1.00)
        mix_at(b, tik_seat, 0.004, 0.78 if not heavy_russian else 0.62)
        mix_at(b, hp(click, 900.0), 0.008, 0.58)
        cues["S_SVCH_MagSeat"] = fin(b, pk_db=-2.0, hp_hz=60.0)

        # 5. ChargePull (0.30 s @ Equip 0.533 s & Empty 2.583 s — 0.30..0.33 s gap before ChargeRelease!):
        # Crisp left-side straight-pull 7.62x54R bolt carrier rail draw + hard steel rear stop!
        b = np.zeros((2, int(round(0.30 * SR))), dtype=np.float64)
        sks_pull = norm(cut("SKS/U_3.wav", 0.528, 0.26, speed=sp * 1.02, fade_in_ms=1.0, fade_out_ms=36.0))
        ak_pull = norm(cut("AK-47/C_0.wav", 0.345, 0.24, speed=sp * 0.98, fade_in_ms=1.0, fade_out_ms=36.0))
        tik_bolt = norm(cut("Tikka/W_9.wav", 0.380, 0.22, speed=sp * 1.04, fade_in_ms=1.0, fade_out_ms=34.0))
        ar_rail = norm(cut("AR-15/D_9.wav", 0.425, 0.22, speed=sp * 1.06, fade_in_ms=1.5, fade_out_ms=36.0))
        mix_at(b, sks_pull, 0.000, 0.88 if heavy_russian else 0.72)
        mix_at(b, ak_pull, 0.015, 0.92 if heavy_russian else 0.70)
        mix_at(b, tik_bolt, 0.005, 0.86 if not heavy_russian else 0.55)
        mix_at(b, hp(ar_rail, 500.0), 0.000, 0.58 if not heavy_russian else 0.36)
        cues["S_SVCH_ChargePull"] = fin(b, pk_db=-2.2, hp_hz=70.0, comp_db=5.5)

        # 6. ChargeRelease (0.38 s @ Equip 0.833 s & Empty 2.917 s):
        # Thunderous precision 7.62x54R steel bolt carrier slamming forward into battery + subtle handguard return settle!
        b = np.zeros((2, int(round(0.38 * SR))), dtype=np.float64)
        ak_rel = norm(cut("AK-47/C_1.wav", 0.295, 0.22, speed=sp * 0.94, fade_in_ms=0.5, fade_out_ms=42.0))
        sks_rel = norm(cut("SKS/U_4.wav", 1.730, 0.22, speed=sp * 0.96, fade_in_ms=0.5, fade_out_ms=40.0))
        tik_rel = norm(cut("Tikka/W_12.wav", 0.528, 0.20, speed=sp * 1.00, fade_in_ms=0.5, fade_out_ms=38.0))
        ar_drop = norm(cut("AR-15/D_13.wav", 0.350, 0.14, speed=sp * 0.98, fade_in_ms=0.4, fade_out_ms=30.0))
        mix_at(b, ak_rel, 0.000, 0.86 if not heavy_russian else 1.00)
        mix_at(b, sks_rel, 0.006, 0.74 if not heavy_russian else 0.90)
        mix_at(b, tik_rel, 0.002, 0.88 if not heavy_russian else 0.62)
        mix_at(b, hp(ar_drop, 800.0), 0.014, 0.62 if not heavy_russian else 0.45)
        # Subtle gloved handguard settle right after bolt lock (0.19 s)
        settle = norm(cut("AR-15/D_18.wav", 0.488, 0.15, speed=0.94, fade_in_ms=8.0, fade_out_ms=45.0))
        mix_at(b, lp(settle, 1800.0), 0.185, 0.22)
        cues["S_SVCH_ChargeRelease"] = fin(b, pk_db=-1.5, hp_hz=50.0, comp_db=5.8, fo_ms=38.0)

        return cues

    for tag, hr, eq_prev, rel_prev in [
        (
            "V1_ModernCNC_Precision",
            False,
            "PREVIEW_5_SVCH_Equip_V1_ModernCNC_Precision.wav",
            "PREVIEW_7_SVCH_ReloadEmpty_V1_ModernCNC_Precision.wav",
        ),
        (
            "V2_HeavyRussianSteel",
            True,
            "PREVIEW_6_SVCH_Equip_V2_HeavyRussianSteel.wav",
            "PREVIEW_8_SVCH_ReloadEmpty_V2_HeavyRussianSteel.wav",
        ),
    ]:
        d = OUT / f"Mechanics_{tag}"
        cues = compose_svch_mechanics(hr)
        for name, clip in cues.items():
            records.append(write_wav_24bit(d / f"{name}.wav", clip))

        # Exact A_SVD_equip timeline (1.70 s): 0.000 s Raise -> 0.533 s Pull -> 0.833 s Release (played twice in preview!)
        eq_one = render_timeline(
            1.40,
            [
                (0.000, cues["S_SVCH_EquipRaise"], 1.0),
                (64.0 / 120.0, cues["S_SVCH_ChargePull"], 1.0),
                (100.0 / 120.0, cues["S_SVCH_ChargeRelease"], 1.0),
            ],
        )
        eq_double = render_timeline(3.30, [(0.00, eq_one, 1.0), (1.85, eq_one, 1.0)])
        records.append(write_wav_24bit(OUT / eq_prev, eq_double))

        # Exact A_SVD_reload_empty timeline (4.29 s): 0.433 MagOut -> 1.833 MagInsert -> 2.000 MagSeat -> 2.583 ChargePull -> 2.917 ChargeRelease
        rel_emp = render_timeline(
            3.85,
            [
                (52.0 / 120.0, cues["S_SVCH_MagOut"], 1.0),
                (220.0 / 120.0, cues["S_SVCH_MagInsert"], 1.0),
                (240.0 / 120.0, cues["S_SVCH_MagSeat"], 1.0),
                (310.0 / 120.0, cues["S_SVCH_ChargePull"], 1.0),
                (350.0 / 120.0, cues["S_SVCH_ChargeRelease"], 1.0),
            ],
        )
        records.append(write_wav_24bit(OUT / rel_prev, rel_emp))

    manifest = {
        "batch": "SVCHAudioRealCC0_20261126",
        "source": "The Free Firearm Sound Library (CC0 1.0 Universal, 192 kHz / 24-bit True Stereo: Mosin 7.62x54R, Tikka .30-06, SKS, Savage 10 .300 BLK, AK-47, AR-15)",
        "output_format": "48 kHz / 24-bit True Stereo PCM",
        "files": records,
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

    print("\n=== SVCh 7.62x54mmR CC0 STUDIO CANDIDATES (48 kHz / 24-bit Stereo) ===")
    print(f"{'File':56s} {'Dur':>5s} {'Pk':>6s} {'RMS':>6s} {'RMS80':>6s} {'Lo%':>5s} {'Mid%':>5s} {'Hi%':>5s}")
    for rec in records:
        f = str(rec["file"])
        if f.startswith("PREVIEW_") or f.endswith("_01.wav") or f.endswith("ChargeRelease.wav") or f.endswith("EquipRaise.wav"):
            print(
                f"{f:56s} {rec['duration_s']:5.2f} {rec['peak_dbfs']:6.1f} {rec['rms_dbfs']:6.1f} "
                f"{rec['rms80_dbfs']:6.1f} {rec['lo_pct']:5.1f} {rec['mid_pct']:5.1f} {rec['hi_pct']:5.1f}"
            )
    print(f"Total files generated: {len(records)}")


if __name__ == "__main__":
    main()
