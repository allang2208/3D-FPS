"""Read retained body objects for the production collision-envelope fit."""
import json
import bpy
from pathlib import Path

bpy.ops.wm.open_mainfile(filepath='D:/FPS3D/FPSGAME/SourceAssets/BlindSupplicantM07Meshy20261001/PalmArmMotionV20/Motion/M07_Original_PalmArmMotion_V20.blend')
rows = [dict(name=o.name, vertices=len(o.data.vertices), hidden=o.hide_viewport,
             groups=[g.name for g in o.vertex_groups][:6]) for o in bpy.data.objects if o.type == 'MESH']
print('M07_BODY_FIT_OBJECTS '+json.dumps(rows), flush=True)
