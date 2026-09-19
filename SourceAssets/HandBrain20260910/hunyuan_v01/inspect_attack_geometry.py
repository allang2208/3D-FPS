import bpy,json
from pathlib import Path
root=Path(__file__).resolve().parent
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(root.parent/'hunyuan_attack_source_v01/handbrain_hunyuan_attack_source_v01_clean.glb'))
o=next(o for o in bpy.context.scene.objects if o.type=='MESH')
points=[o.matrix_world@v.co for v in o.data.vertices]
report=[]
for y in [-1.6,-1.4,-1.2,-1,-.8,-.6,-.4,-.2,0]:
    ps=[p for p in points if y-.05<=p.y<=y+.05]
    if ps:report.append({'y':y,'count':len(ps),'bounds':[[min(p[k] for p in ps),max(p[k] for p in ps)] for k in range(3)]})
print(json.dumps(report,indent=2))
