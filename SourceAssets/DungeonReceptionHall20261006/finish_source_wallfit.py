"""Match editable source placement to the final map; no re-export of shared meshes."""
from pathlib import Path
import bpy,json
ROOT=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'Authored/FacilityReceptionHall.blend'))
for kind in ('WallClock','ClockHands'):bpy.data.objects['SM_Reception_'+kind].location=(0,.12,0)
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'Authored/FacilityReceptionHall.blend'))
manifest=json.loads((ROOT/'manifest.json').read_text('utf8'))
for m in manifest['meshes']:
    if m['kind'] in ('WallClock','ClockHands'):m['position_m']=[0,.12,0]
(ROOT/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf8')
