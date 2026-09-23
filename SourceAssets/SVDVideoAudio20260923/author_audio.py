"""Sample-accurate SVD excerpts from the user-selected Bilibili soundtrack.

Roles are inferred from the SVD animation and waveform transients, not from
isolated recording stems. Preserve the downloaded AAC and unedited float cuts.
"""
from pathlib import Path
import hashlib
import json
import subprocess

import imageio_ffmpeg
import numpy as np
import soundfile as sf

ROOT = Path(__file__).resolve().parent
URL = "https://www.bilibili.com/video/BV15MqbBcEQh/"
SOURCE = ROOT / "source_audio.m4a"
# Video timeline in seconds. Use the isolated shot with a complete decay;
# rapid follow-up shots in the comparison overlap and are not clean variants.
CUES = {
    "Fire_01": (117.465, 118.335),
    "MagOut": (111.800, 112.085),
    "MagInsert": (112.985, 113.170),
    "MagSeat": (113.170, 113.430),
    "ChargePull": (114.080, 114.255),
    "ChargeRelease": (114.255, 114.515),
}
REFERENCES = {
    "SVD_Reload_Full_01": (111.400, 114.700),
    "SVD_Reload_Full_02": (121.100, 124.550),
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    audio_dir = ROOT / "Audio"
    master_dir = ROOT / "Masters"
    for directory in (audio_dir, master_dir):
        directory.mkdir(exist_ok=True)
    decoded = ROOT / "reference_110_end_float.wav"
    subprocess.run([
        imageio_ffmpeg.get_ffmpeg_exe(), "-v", "error", "-y", "-i", str(SOURCE),
        "-ss", "110", "-vn", "-c:a", "pcm_f32le", str(decoded),
    ], check=True)
    x, rate = sf.read(decoded, always_2d=True, dtype="float32")
    records = []
    for cue, (start, end) in CUES.items():
        first, last = round((start - 110) * rate), round((end - 110) * rate)
        raw = x[first:last].copy()
        name = "S_SVD_" + cue
        master = master_dir / (name + "_float.wav")
        sf.write(master, raw, rate, subtype="FLOAT")
        edited = raw.astype(np.float64)
        # Retain native sample rate, stereo, pitch, and source relative levels.
        # Only tiny edge fades and overload protection; no EQ/denoise/time warp.
        fade_in = round(0.00025 * rate)
        fade_out = round(0.008 * rate)
        edited[:fade_in] *= np.linspace(0, 1, fade_in)[:, None]
        edited[-fade_out:] *= np.linspace(1, 0, fade_out)[:, None]
        peak = float(np.max(np.abs(edited)))
        gain = min(1.0, 0.95 / max(peak, 1e-12))
        edited *= gain
        destination = audio_dir / (name + ".wav")
        sf.write(destination, edited, rate, subtype="PCM_16")
        records.append({
            "cue": cue, "name": name, "source_start": start, "source_end": end,
            "offset_samples_in_110s_reference": [first, last],
            "duration": len(raw) / rate, "sample_rate": rate, "channels": raw.shape[1],
            "gain": gain, "peak_before_gain": peak,
            "master": str(master.relative_to(ROOT)),
            "file": str(destination.relative_to(ROOT)), "sha256": sha(destination),
        })
    for name, (start, end) in REFERENCES.items():
        raw = x[round((start - 110) * rate):round((end - 110) * rate)]
        sf.write(master_dir / (name + "_float.wav"), raw, rate, subtype="FLOAT")
    provenance = {
        "source_url": URL, "source_bvid": "BV15MqbBcEQh", "source_uploader": "127毫米",
        "source_title": "三角洲音效对比 PSG-1&SR25&SVD",
        "source_audio": "source_audio.m4a", "source_audio_sha256": sha(SOURCE),
        "source_video_sha256": sha(ROOT / "source_video.mp4"),
        "source_format": "Bilibili format 30280, AAC LC, approx 125.372 kbps, 44100 Hz stereo",
        "request_start": 110.0,
        "identification": "SVD label and game animation frames plus soundtrack transients. No listening review performed.",
        "authenticity": "Video comparison soundtrack; independent real-SVD recording provenance is not established.",
        "rights": "User-directed local extraction. Third-party rights retained; no public redistribution license established. Not CC0.",
        "quality": "Lossy AAC source. Unedited decoded samples retained as float32 WAV; runtime PCM16 WAV adds no perceptual encoding. Not an original lossless recording.",
        "processing": "Sample slicing; runtime only: 0.25 ms fade-in, 8 ms fade-out, peak protection to 0.95 only when needed. No upsampling, pitch/time change, denoise or EQ.",
        "cues": records,
        "reference_segments": REFERENCES,
        "game_tested": False,
    }
    (ROOT / "provenance.json").write_text(json.dumps(provenance, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"authored": len(records), "rate": rate, "cues": records}, ensure_ascii=True))


if __name__ == "__main__":
    main()
