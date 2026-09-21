"""Prepare original skill audio without mixing it with unrelated weather thunder."""
import hashlib
import json
from pathlib import Path
import subprocess
import imageio_ffmpeg

ROOT=Path(__file__).resolve().parents[2]
SOURCE=Path('E:/无尽轮回/长期备份/2026-7-13-1/game-dev/assets/sounds/skills')
DEST=ROOT/'SourceAssets/Lightning20260920'
DEST.mkdir(parents=True,exist_ok=True)
records=[]
for i in (1,2):
    source=SOURCE/f'lightning-{i}.mp3'
    target=DEST/f'S_LightningCast{i}.wav'
    subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(),'-y','-v','error','-i',str(source),'-ar','48000','-ac','1','-c:a','pcm_s16le',str(target)],check=True)
    records.append({'source':str(source),'sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'derived':str(target),'rights':'Existing user project audio; original redistribution rights not independently established. Local use only.'})
(DEST/'audio-provenance.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
print('Prepared two original lightning cast waves')
