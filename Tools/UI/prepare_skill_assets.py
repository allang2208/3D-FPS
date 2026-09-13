"""Prepare the existing game-dev rifle icon and upgrade cue for UE's UFS runtime loader."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import wave
import imageio_ffmpeg

PROJECT = Path(__file__).resolve().parents[2]
SOURCE = Path(r"E:/无尽轮回/长期备份/2026-7-13-1/game-dev")
ORIGINALS = PROJECT / "SourceAssets/Skills20260913"
RUNTIME = PROJECT / "Content/ColdSteelData/Skills"

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    ORIGINALS.mkdir(parents=True, exist_ok=True)
    RUNTIME.mkdir(parents=True, exist_ok=True)
    icon = SOURCE / "assets/skills/步枪精通.png"
    sound = SOURCE / "assets/sounds/ui/player_upgrade.mp3"
    shutil.copy2(icon, ORIGINALS / "rifle_mastery.png")
    shutil.copy2(icon, RUNTIME / "rifle_mastery.png")
    shutil.copy2(sound, ORIGINALS / "player_upgrade.mp3")
    wav = RUNTIME / "player_upgrade.wav"
    subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-hide_banner", "-loglevel", "error", "-y",
                    "-i", str(sound), "-vn", "-ar", "44100", "-ac", "2", "-c:a", "pcm_s16le", str(wav)], check=True)
    with wave.open(str(wav), "rb") as data:
        metadata = {"sampleRate": data.getframerate(), "channels": data.getnchannels(),
                    "bits": data.getsampwidth() * 8, "durationSeconds": data.getnframes()/data.getframerate()}
    manifest = {"sourceProject": str(SOURCE), "sourceConfig": "data/audio-config.json:uiCues.playerUpgrade",
                "usage": "Reuse from the user's existing project; no new redistribution license asserted. Source binaries stay local.",
                "icon": {"source": str(icon), "sha256": digest(icon), "runtime": "Skills/rifle_mastery.png", "operation": "unchanged copy"},
                "audio": {"source": str(sound), "sourceSha256": digest(sound), "runtime": "Skills/player_upgrade.wav", "sha256": digest(wav), **metadata}}
    (ORIGINALS / "provenance.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    print(json.dumps(metadata, ensure_ascii=False))

if __name__ == "__main__":
    main()
