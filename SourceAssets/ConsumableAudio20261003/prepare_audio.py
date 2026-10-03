"""Decode the four user-provided recordings to UE-importable PCM WAVs."""
from pathlib import Path
import json
import subprocess
import wave

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
SOURCE = Path("D:/FPS3D/资产/音效")
FFMPEG = ROOT / "SourceAssets/M4Infima/PreviewTools/imageio_ffmpeg/binaries/ffmpeg-win-x86_64-v7.1.exe"
RECORDINGS = {
    "S_WaterSwallow_01": "吞咽水.mp3",
    "S_WaterSwallow_02": "吞咽水2.mp3",
    "S_WaterSwallow_03": "吞咽水3.mp3",
    "S_FoodSwallow": "吞咽食物.mp3",
}

(OUT / "Wav").mkdir(parents=True, exist_ok=True)
manifest = {"source": str(SOURCE), "destination": "/Game/Audio/Consumables20261003", "recordings": []}
for asset_name, filename in RECORDINGS.items():
    source = SOURCE / filename
    destination = OUT / "Wav" / (asset_name + ".wav")
    subprocess.run([
        str(FFMPEG), "-y", "-hide_banner", "-loglevel", "error",
        "-i", str(source), "-map", "0:a:0", "-vn",
        "-ar", "48000", "-ac", "2", "-c:a", "pcm_s16le", str(destination),
    ], check=True)
    with wave.open(str(destination), "rb") as recording:
        duration = recording.getnframes() / recording.getframerate()
    manifest["recordings"].append({
        "asset_name": asset_name, "source": str(source), "wav": str(destination), "duration_seconds": duration,
    })
    print(f"Prepared {asset_name}: {duration:.3f}s")
(OUT / "audio_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
