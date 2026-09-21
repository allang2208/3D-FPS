"""Convert the legacy holy-light cast audio for the local UE project."""
from pathlib import Path
import hashlib
import json
import subprocess
import imageio_ffmpeg

ROOT=Path(__file__).resolve().parents[2]
SOURCE=Path('E:/无尽轮回/长期备份/2026-7-13-1/game-dev/assets/sounds/skills/holy-light-1.mp3')
DEST=ROOT/'SourceAssets/HolyLight20260920'
DEST.mkdir(parents=True,exist_ok=True)
WAVE=DEST/'S_HolyLightCast.wav'
subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(),'-y','-v','error','-i',str(SOURCE),'-ar','48000','-ac','1','-c:a','pcm_s16le',str(WAVE)],check=True)
(DEST/'provenance.json').write_text(json.dumps({'sound':{'source':str(SOURCE),'sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),'derived':str(WAVE),'rights':'Existing user project audio; local use, redistribution rights not independently established.'},'niagara':{'source':'/Game/_SplineVFX/NS/NS_Spline_Holy','pack':'Existing licensed Dr.Game Free Spline VFX','use':'Project-owned copy of Detail002; keep the original pack intact.'},'icon':'imagegen generated for this task, graphite background, silver frame, golden pillar'},ensure_ascii=False,indent=2),encoding='utf-8')
print('Prepared original holy-light cast audio')
