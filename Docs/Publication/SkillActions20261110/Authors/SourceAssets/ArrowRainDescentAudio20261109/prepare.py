"""Reuse the normal bow release recording without changing its timbre or timing."""
import hashlib
import json
import shutil
from pathlib import Path
import wave

ROOT = Path('D:/FPS3D/FPSGAME')
OUT = Path(__file__).resolve().parent
SOURCE_ASSET = '/Game/Weapons/DarkBow20260925/AudioVideoDirect20260926/S_BowVideoDirect_Release.S_BowVideoDirect_Release'
SOURCE_WAV = ROOT / 'SourceAssets/BowVideoAudioDirect20260926/Wav/S_BowVideoDirect_Release.wav'


def prepare(source=None):
    source = Path(source) if source else SOURCE_WAV
    with wave.open(str(source), 'rb') as audio:
        rate, channels, frames = audio.getframerate(), audio.getnchannels(), audio.getnframes()
    target = OUT / 'S_ArrowRainBurst.wav'
    shutil.copy2(source, target)
    # Keep the established full skill authoring pipeline pointed at this selection.
    shutil.copy2(target, ROOT / 'SourceAssets/MagicArrowRain20261026/S_ArrowRainBurst.wav')
    receipt = dict(source=str(source), source_asset=SOURCE_ASSET, selection='Normal bow release; staggered sequence unchanged',
                   source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                   exported_seconds=frames/rate, channels=channels, sample_rate=rate,
                   gain=1., wave=str(target), runtime_tested=False, auditioned=False)
    (OUT / 'prepared-audio.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(receipt, ensure_ascii=False))


if __name__ == '__main__':
    prepare()
