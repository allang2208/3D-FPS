"""Produce the standard 2x2 inventory icon from the actual helmet game mesh."""
import bpy,json,importlib.util,copy
from pathlib import Path
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/ModernTacticalSet20261113/HelmetDetailR1'
spec=importlib.util.spec_from_file_location('helmet_inventory',P/'Tools/ModernTacticalSet/prepare_delivery.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);m.OUT=R/'Icons'
bpy.ops.wm.open_mainfile(filepath=str(R/'Models/TS01_Helmet_Jason_GAME.blend'))
for ob in list(bpy.data.objects):
    if ob.name.startswith('REFERENCE_ONLY_'):bpy.data.objects.remove(ob,do_unlink=True)
ob=m.combine();ob.name='TS01_Helmet_Display';icon=m.icon(ob,'ue_modern_tactical_helmet',2,2,'helmet')
d=json.loads((R/'Authored/helmet_Jason_world.json').read_text(encoding='utf-8'))
for axis in range(3):
    center=(min(p[axis] for p in d['positions'])+max(p[axis] for p in d['positions']))*.5
    for p in d['positions']:p[axis]-=center
(R/'Authored/helmet_pickup.json').write_text(json.dumps(d,separators=(',',':')),encoding='utf-8')
(R/'artwork.json').write_text(json.dumps(dict(completed=True,icon=icon,pickup=str(R/'Authored/helmet_pickup.json')),indent=2),encoding='utf-8');print('HELMET_STANDARD_ARTWORK_SAVED',flush=True)
