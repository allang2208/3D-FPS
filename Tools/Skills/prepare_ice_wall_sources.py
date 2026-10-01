"""Restore the selected generated ice-wall icon and convert the original cast sound."""
import json, shutil, subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / 'SourceAssets/IceWall20260930'
SRC.mkdir(parents=True, exist_ok=True)
icon = ROOT/'SourceAssets/IceSkillIcons20260930/ice_wall_cold_steel.png'
if not icon.is_file():
    raise FileNotFoundError('Restore the generated Cold Steel ice-wall icon: '+str(icon))
runtime = ROOT/'Content/ColdSteelData/Skills';runtime.mkdir(parents=True, exist_ok=True)
shutil.copy2(icon, runtime/'ice_wall_cold_steel.png')
source = Path('E:/无尽轮回/长期备份/2026-7-13-1/game-dev/assets/sounds/skills/icewall.mp3')
if source.exists():
    shutil.copy2(source, SRC/'icewall.mp3')
    import imageio_ffmpeg
    subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), '-y','-i',str(SRC/'icewall.mp3'),
        '-ar','44100','-ac','1',str(SRC/'icewall.wav')],check=True)
    (SRC/'sound-source.json').write_text(json.dumps({'source':str(source),'use':'local migration; redistribution license not asserted'},ensure_ascii=False,indent=2),encoding='utf-8')
