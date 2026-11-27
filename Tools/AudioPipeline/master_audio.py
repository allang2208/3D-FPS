"""Deterministic local audio mastering for FPSGAME UE5 SoundWave production.

Turns user-selected raw candidate WAVs into 48 kHz, 24-bit PCM WAV masters with:
  - optional head/tail silence trim (recording trimmed_lead_ms for contact alignment)
  - Butterworth high-pass rumble removal
  - equal-power tail-fold seamless looping (prevents click seams per monster-audio.md)
  - mono downmix (3D spatial) or stereo preservation (1P/UI/BGM)
  - RMS + peak ceiling normalization without clipping
  - full SHA-256 provenance manifest for byte-level reproducibility
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from math import gcd
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import soundfile as sf
from scipy import signal

TARGET_SR = 48000

PRESETS: Dict[str, Dict[str, Any]] = {
    "sfx_spatial": {
        "mono": True,
        "highpass_hz": 45.0,
        "trim_head": True,
        "trim_tail": True,
        "trim_threshold_db": -46.0,
        "pre_pad_ms": 2.0,
        "post_pad_ms": 25.0,
        "fade_in_ms": 1.5,
        "fade_out_ms": 15.0,
        "loop_crossfade_sec": 0.0,
        "target_rms_dbfs": -16.0,
        "peak_ceiling_dbfs": -1.5,
    },
    "sfx_oneshot": {
        "mono": False,
        "highpass_hz": 35.0,
        "trim_head": True,
        "trim_tail": True,
        "trim_threshold_db": -48.0,
        "pre_pad_ms": 1.5,
        "post_pad_ms": 25.0,
        "fade_in_ms": 1.0,
        "fade_out_ms": 15.0,
        "loop_crossfade_sec": 0.0,
        "target_rms_dbfs": -14.0,
        "peak_ceiling_dbfs": -1.3,
    },
    "ambience_loop": {
        "mono": False,
        "highpass_hz": 35.0,
        "trim_head": False,
        "trim_tail": False,
        "trim_threshold_db": -55.0,
        "pre_pad_ms": 0.0,
        "post_pad_ms": 0.0,
        "fade_in_ms": 0.0,
        "fade_out_ms": 0.0,
        "loop_crossfade_sec": 0.6,
        "target_rms_dbfs": -18.0,
        "peak_ceiling_dbfs": -3.0,
    },
    "bgm": {
        "mono": False,
        "highpass_hz": 28.0,
        "trim_head": False,
        "trim_tail": False,
        "trim_threshold_db": -55.0,
        "pre_pad_ms": 0.0,
        "post_pad_ms": 0.0,
        "fade_in_ms": 15.0,
        "fade_out_ms": 40.0,
        "loop_crossfade_sec": 0.0,
        "target_rms_dbfs": -16.0,
        "peak_ceiling_dbfs": -1.5,
    },
    "voice": {
        "mono": True,
        "highpass_hz": 80.0,
        "trim_head": True,
        "trim_tail": True,
        "trim_threshold_db": -45.0,
        "pre_pad_ms": 15.0,
        "post_pad_ms": 40.0,
        "fade_in_ms": 5.0,
        "fade_out_ms": 20.0,
        "loop_crossfade_sec": 0.0,
        "target_rms_dbfs": -16.0,
        "peak_ceiling_dbfs": -1.5,
    },
}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def db_to_lin(db: float) -> float:
    return float(10.0 ** (db / 20.0))


def lin_to_db(val: float) -> float:
    return round(float(20.0 * np.log10(max(val, 1e-9))), 2)


def resample_audio(data: np.ndarray, orig_sr: int, target_sr: int) -> np.ndarray:
    if orig_sr == target_sr:
        return data
    d = gcd(orig_sr, target_sr)
    up, down = target_sr // d, orig_sr // d
    cols = [signal.resample_poly(data[:, c], up, down) for c in range(data.shape[1])]
    return np.stack(cols, axis=1).astype(np.float64)


def make_seamless_loop(data: np.ndarray, sr: int, xfade_sec: float) -> np.ndarray:
    """Fold tail back into head with equal-power sine/cosine crossfade."""
    n = data.shape[0]
    xf = int(round(sr * xfade_sec))
    if xf <= 0 or n <= xf * 2 + 16:
        return data
    body = data[:-xf].copy()
    tail = data[-xf:]
    t = np.linspace(0.0, np.pi * 0.5, xf, dtype=np.float64)[:, None]
    fade_in = np.sin(t)
    fade_out = np.cos(t)
    body[:xf] = body[:xf] * fade_in + tail * fade_out
    return body


def process_one(input_path: Path, output_path: Path, cfg: Dict[str, Any]) -> Dict[str, Any]:
    raw, orig_sr = sf.read(str(input_path), always_2d=True)
    audio = raw.astype(np.float64)
    src_sha = sha256_file(input_path)

    # 1. Channel layout
    if cfg.get("mono", False) and audio.shape[1] > 1:
        audio = audio.mean(axis=1, keepdims=True)

    # 2. DC offset removal + highpass filter before resampling/cutting
    audio -= np.mean(audio, axis=0, keepdims=True)
    hp_hz = float(cfg.get("highpass_hz", 0.0))
    if hp_hz > 0.0 and hp_hz < orig_sr * 0.45:
        sos = signal.butter(2, hp_hz, btype="highpass", fs=orig_sr, output="sos")
        audio = signal.sosfiltfilt(sos, audio, axis=0)

    # 3. Resample to 48 kHz
    audio = resample_audio(audio, orig_sr, TARGET_SR)
    sr = TARGET_SR

    # 4. Optional explicit clip window (start_sec / end_sec)
    trimmed_lead_ms = 0.0
    start_sec = cfg.get("start_sec")
    end_sec = cfg.get("end_sec")
    if start_sec is not None or end_sec is not None:
        s0 = max(0, int(round(float(start_sec or 0.0) * sr)))
        s1 = min(audio.shape[0], int(round(float(end_sec) * sr))) if end_sec is not None else audio.shape[0]
        audio = audio[s0:s1]
        trimmed_lead_ms += (s0 / float(sr)) * 1000.0

    # 5. Automatic silence trim
    peak = float(np.max(np.abs(audio))) if audio.size else 0.0
    if peak > 1e-7 and (cfg.get("trim_head") or cfg.get("trim_tail")):
        env = np.max(np.abs(audio), axis=1)
        thresh = peak * db_to_lin(float(cfg.get("trim_threshold_db", -46.0)))
        above = np.flatnonzero(env >= thresh)
        if len(above):
            i0 = int(above[0]) if cfg.get("trim_head") else 0
            i1 = int(above[-1]) + 1 if cfg.get("trim_tail") else audio.shape[0]
            pre = int(round(float(cfg.get("pre_pad_ms", 2.0)) * 0.001 * sr))
            post = int(round(float(cfg.get("post_pad_ms", 25.0)) * 0.001 * sr))
            c0 = max(0, i0 - pre) if cfg.get("trim_head") else 0
            c1 = min(audio.shape[0], i1 + post) if cfg.get("trim_tail") else audio.shape[0]
            audio = audio[c0:c1]
            trimmed_lead_ms += (c0 / float(sr)) * 1000.0

    # 6. Optional max duration clamp
    max_dur = cfg.get("max_duration_sec")
    if max_dur is not None and float(max_dur) > 0:
        max_samples = int(round(float(max_dur) * sr))
        if audio.shape[0] > max_samples:
            audio = audio[:max_samples]

    # 7. Seamless loop OR short edge fades
    xfade_sec = float(cfg.get("loop_crossfade_sec", 0.0))
    if xfade_sec > 0.0:
        audio = make_seamless_loop(audio, sr, xfade_sec)
    else:
        fi = min(audio.shape[0] // 4, int(round(float(cfg.get("fade_in_ms", 1.5)) * 0.001 * sr)))
        fo = min(audio.shape[0] // 3, int(round(float(cfg.get("fade_out_ms", 15.0)) * 0.001 * sr)))
        if fi > 1:
            audio[:fi] *= np.linspace(0.0, 1.0, fi)[:, None]
        if fo > 1:
            audio[-fo:] *= (np.cos(np.linspace(0.0, np.pi * 0.5, fo)) ** 2)[:, None]

    # 8. RMS + Peak ceiling normalization (never clips)
    mono = audio.mean(axis=1)
    cur_rms = float(np.sqrt(np.mean(mono * mono))) if mono.size else 0.0
    cur_peak = float(np.max(np.abs(audio))) if audio.size else 0.0
    ceiling = db_to_lin(float(cfg.get("peak_ceiling_dbfs", -1.5)))
    target_rms_db = cfg.get("target_rms_dbfs")
    gain = 1.0
    if cur_peak > 1e-8:
        if target_rms_db is not None and cur_rms > 1e-8:
            desired_gain = db_to_lin(float(target_rms_db)) / cur_rms
            max_safe_gain = ceiling / cur_peak
            gain = min(desired_gain, max_safe_gain)
        else:
            gain = ceiling / cur_peak
        audio = audio * gain

    output_path.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(output_path), audio.astype(np.float32), sr, subtype="PCM_24")

    final_mono = audio.mean(axis=1)
    final_peak = float(np.max(np.abs(audio))) if audio.size else 0.0
    final_rms = float(np.sqrt(np.mean(final_mono * final_mono))) if final_mono.size else 0.0
    return {
        "source_path": str(input_path),
        "source_sha256": src_sha,
        "master_path": str(output_path),
        "master_sha256": sha256_file(output_path),
        "orig_sample_rate": int(orig_sr),
        "sample_rate": sr,
        "bit_depth": 24,
        "channels": int(audio.shape[1]),
        "duration_sec": round(audio.shape[0] / float(sr), 4),
        "trimmed_lead_ms": round(trimmed_lead_ms, 2),
        "applied_gain_db": lin_to_db(gain),
        "peak_dbfs": lin_to_db(final_peak),
        "rms_dbfs": lin_to_db(final_rms),
        "seamless_loop": xfade_sec > 0.0,
        "dsp": cfg,
    }


def run_batch(spec_path: Path) -> None:
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    base_dir = spec_path.parent
    results: List[Dict[str, Any]] = []
    for item in spec["items"]:
        preset_name = item.get("preset", "sfx_spatial")
        cfg = dict(PRESETS[preset_name])
        cfg.update(item.get("dsp") or {})
        inp = Path(item["input"])
        if not inp.is_absolute():
            inp = (base_dir / inp).resolve()
        out = Path(item["output"])
        if not out.is_absolute():
            out = (base_dir / out).resolve()
        res = process_one(inp, out, cfg)
        res["name"] = item.get("name", out.stem)
        res["preset"] = preset_name
        results.append(res)

    manifest_path = Path(spec.get("manifest_out") or (base_dir / "master_manifest.json"))
    if not manifest_path.is_absolute():
        manifest_path = (base_dir / manifest_path).resolve()
    manifest = {
        "schema_version": 1,
        "mastered_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "spec_path": str(spec_path.resolve()),
        "user_auditioned": False,
        "gameplay_tested": False,
        "items": results,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Mastered {len(results)} file(s) -> {manifest_path}")


def main() -> None:
    p = argparse.ArgumentParser(description="FPSGAME Local 48kHz/24-bit Audio Mastering")
    p.add_argument("--spec", default=None, help="Batch JSON spec path (overrides single-file flags)")
    p.add_argument("--input", default=None, help="Single input candidate WAV path")
    p.add_argument("--output", default=None, help="Single output master WAV path")
    p.add_argument("--preset", default="sfx_spatial", choices=sorted(PRESETS.keys()))
    p.add_argument("--mono", action="store_true", help="Force mono downmix")
    p.add_argument("--stereo", action="store_true", help="Preserve stereo")
    p.add_argument("--highpass-hz", type=float, default=None)
    p.add_argument("--loop-crossfade-sec", type=float, default=None)
    p.add_argument("--target-rms-dbfs", type=float, default=None)
    p.add_argument("--peak-ceiling-dbfs", type=float, default=None)
    p.add_argument("--start-sec", type=float, default=None)
    p.add_argument("--end-sec", type=float, default=None)
    p.add_argument("--max-duration-sec", type=float, default=None)
    p.add_argument("--no-trim", action="store_true")
    p.add_argument("--manifest", default=None, help="Optional output manifest JSON path")
    args = p.parse_args()

    if args.spec:
        run_batch(Path(args.spec).resolve())
        return

    if not args.input or not args.output:
        raise SystemExit("Provide either --spec <batch.json> or both --input and --output.")

    cfg = dict(PRESETS[args.preset])
    if args.mono:
        cfg["mono"] = True
    if args.stereo:
        cfg["mono"] = False
    if args.highpass_hz is not None:
        cfg["highpass_hz"] = args.highpass_hz
    if args.loop_crossfade_sec is not None:
        cfg["loop_crossfade_sec"] = args.loop_crossfade_sec
    if args.target_rms_dbfs is not None:
        cfg["target_rms_dbfs"] = args.target_rms_dbfs
    if args.peak_ceiling_dbfs is not None:
        cfg["peak_ceiling_dbfs"] = args.peak_ceiling_dbfs
    if args.start_sec is not None:
        cfg["start_sec"] = args.start_sec
    if args.end_sec is not None:
        cfg["end_sec"] = args.end_sec
    if args.max_duration_sec is not None:
        cfg["max_duration_sec"] = args.max_duration_sec
    if args.no_trim:
        cfg["trim_head"] = False
        cfg["trim_tail"] = False

    inp = Path(args.input).resolve()
    out = Path(args.output).resolve()
    res = process_one(inp, out, cfg)
    res["preset"] = args.preset
    if args.manifest:
        mpath = Path(args.manifest).resolve()
        mpath.parent.mkdir(parents=True, exist_ok=True)
        mpath.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "mastered_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "user_auditioned": False,
                    "gameplay_tested": False,
                    "items": [res],
                },
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
    print(json.dumps(res, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
