import bpy,json,math
from pathlib import Path
P=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(P/'LeiXi/LeiXiPommelV2_Editable.blend'))
o=next(o for o in bpy.context.scene.objects if o.type=='MESH');out=[]
for i in range(25):
 z=-i*.001;vs=[v.co for v in o.data.vertices if abs(v.co.z-z)<.0005]
 if vs:out.append({'z_mm':round(z*1000,1),'radius_mm':round(max(math.hypot(p.x+.0006,p.y+.001) for p in vs)*1000,2)})
print('COLLAR_PROFILE',json.dumps(out),flush=True)
