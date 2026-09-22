import bpy,json,sys
from pathlib import Path
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/WitchRebuilt20260921');OUT=ROOT/'DrapeGrip20260922'
# Reuse the same requested diagnostic with only the input scene changed.
path=Path(__file__).parent/'inspect_drape_grip.py'
code=path.read_text(encoding='utf-8').replace("OUT/'Before/Authoring/WitchRebuilt_Walk.blend'","ROOT/'Authoring/WitchRebuilt_Walk.blend'").replace("OUT/'diagnosis_source.json'","OUT/'source_after.json'")
exec(compile(code,str(path),'exec'))
