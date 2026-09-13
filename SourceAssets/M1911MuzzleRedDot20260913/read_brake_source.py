import bpy,json,math
from pathlib import Path
O=Path(__file__).parent
bpy.ops.wm.open_mainfile(filepath=str(O.parent/'M4Muzzles20260910/brake-editable.blend'))
report=[]
for ob in bpy.context.scene.objects:
    if ob.type!='MESH':continue
    slots={}
    for i,m in enumerate(ob.data.materials):
        indices={vi for p in ob.data.polygons if p.material_index==i for vi in p.vertices}
        radii=sorted(math.hypot(ob.data.vertices[vi].co.x,ob.data.vertices[vi].co.z) for vi in indices)
        slots[m.name]={'radius_samples_m':[radii[int((len(radii)-1)*q)] for q in [0,.05,.25,.5,.75,.95,1]]}
    report.append({'object':ob.name,'slots':slots})
(O/'brake_source.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report),flush=True)
