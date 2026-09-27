"""Publish matching icon and production entrypoints after the saved V19 install."""
import json,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parent;PROJECT=ROOT.parents[2]
path=ROOT/'import-receipt.json';receipt=json.loads(path.read_text(encoding='utf-8'))
if not receipt.get('complete'):raise RuntimeError('V19 import incomplete')
for relative in ('Content/ColdSteelData/Icons/apprentice_staff.png','SourceAssets/ApprenticeStaff20260927/author_staff.py','SourceAssets/ApprenticeStaff20260927/import_staff.py'):
    source=PROJECT/relative;backup=ROOT/'Before'/relative
    backup.parent.mkdir(parents=True,exist_ok=True)
    if not backup.exists():shutil.copy2(source,backup)
shutil.copy2(ROOT/'Export/apprentice_staff.png',PROJECT/'Content/ColdSteelData/Icons/apprentice_staff.png')
for filename in ('author_staff.py','import_staff.py'):
    source=ROOT.parent/filename;s=source.read_text(encoding='utf-8')
    s=s.replace("ROOT/'BranchCrystalV18/", "ROOT/'SolidRepairV19/")
    source.write_text(s,encoding='utf-8')
receipt['metadata_updated']=True
receipt['inventory_icon']='Content/ColdSteelData/Icons/apprentice_staff.png'
receipt['icon_source']='Blender V19 repaired assembly'
receipt['geometry_checks']='geometry_checks.json'
receipt['diagnostic_renders']=['repair_front.png','repair_back.png']
receipt['tested_in_game']=False
receipt['source_fbx_geometry_uv_passed']=json.loads((ROOT/'geometry_checks.json').read_text())['passed']
receipt['saved_ue_geometry_uv_passed']=json.loads((ROOT/'ue_geometry_checks.json').read_text())['passed']
receipt['diagnostic_renderer']='Blender Cycles; not an in-game screenshot'
receipt['rendered']=True
path.write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
print('STAFF_V19_ICON_AND_ENTRYPOINTS_PUBLISHED')
