"""Preserve the old pedestal package and save corrected geometry and UV stone."""
import hashlib
import json
import os
from pathlib import Path
import runpy
import shutil
import unreal as u

ROOT=Path('D:/FPS3D/FPSGAME')
OUT=ROOT/'SourceAssets/ChapelShrineForecourt20261116/SupportFixR2'
OUT.mkdir(parents=True,exist_ok=True)
source=ROOT/'Content/WorldGeneration/HillsNightRaid/SM_ChapelShrineRockPedestal.uasset'
backup=OUT/'Before/SM_ChapelShrineRockPedestal.uasset'
backup.parent.mkdir(exist_ok=True)
if not backup.exists():shutil.copy2(source,backup)
os.environ['CHAPEL_SHRINE_OUTPUT']=str(OUT)
runpy.run_path(str(ROOT/'Tools/WorldGeneration/author_chapel_shrine_pedestal.py'))
material=u.load_asset('/Game/WorldGeneration/HillsNightRaid/M_ChapelShrinePedestalStone')
receipt={'pedestal_saved':True,'before_sha256':hashlib.sha256(backup.read_bytes()).hexdigest(),
         'after_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
         'material':material.get_path_name(),'decal_response':str(material.get_editor_property('material_decal_response')),
         'game_tested':False}
(OUT/'support-fix-saved.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print('CHAPEL_PEDESTAL_SUPPORT_FIX_SAVED',flush=True)
