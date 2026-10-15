"""Read the existing garment pieces needed for the two clothing variants."""
import bpy, json
from mathutils import Vector
from pathlib import Path

bpy.ops.wm.open_mainfile(filepath='D:/FPS3D/FPSGAME/SourceAssets/FacelessSecurity20261008/V13/Authoring/FacelessSecurity_V13.blend')
rows=[]
for o in bpy.context.scene.objects:
    if o.type != 'MESH': continue
    points=[o.matrix_world @ Vector(p) for p in o.bound_box]
    rows.append(dict(name=o.name, vertices=len(o.data.vertices), materials=[m.name for m in o.data.materials],
                     bounds=[[round(min(p[i] for p in points),4),round(max(p[i] for p in points),4)] for i in range(3)]))
rig=bpy.data.objects['root']
result=dict(meshes=rows,head_matrix=[list(r) for r in (rig.matrix_world @ rig.data.bones['head'].matrix_local)])
out=Path('D:/FPS3D/FPSGAME/SourceAssets/CargoStationStaff20261014/V01')
out.mkdir(parents=True,exist_ok=True)
(out/'source_structure.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print('CARGO_SOURCE_READ '+str(len(rows))+' meshes')
