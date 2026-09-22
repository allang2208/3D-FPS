"""Read source-space geometry to choose crop and contact planes before authoring."""
import bpy,json
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1]
result={}
for ident in ('ridge_a','ridge_b','dirt_wall','gravel','stone_scatter','stone_patch','rubble_a'):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(ROOT/'Sources'/(ident+'.fbx')))
    objs=[o for o in bpy.context.scene.objects if o.type=='MESH']
    pts=[o.matrix_world@v.co for o in objs for v in o.data.vertices]
    lo=[min(p[i] for p in pts) for i in range(3)];hi=[max(p[i] for p in pts) for i in range(3)]
    row={'min':lo,'max':hi,'objects':[(o.name,len(o.data.vertices)) for o in objs], 'x_slices':[]}
    for j in range(10):
        sel=[p for p in pts if lo[0]+(hi[0]-lo[0])*j/10<=p.x<=lo[0]+(hi[0]-lo[0])*(j+1)/10]
        row['x_slices'].append([round(lo[0]+(hi[0]-lo[0])*(j+.5)/10,3),round(min(p.z for p in sel),3),round(max(p.z for p in sel),3)] if sel else None)
    result[ident]=row
(ROOT/'Sources/geometry-layout.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result))
