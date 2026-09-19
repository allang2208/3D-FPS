import bpy,json
from pathlib import Path
from mathutils import Vector
r=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(r.parent/'hunyuan_v01/delivery/HandBrain_Animated.blend'))
o=bpy.data.objects['HandBrain_Body']
out=[]
for z in [.65,.7,.72,.74,.76,.78,.8,.82,.84,.86,.9,1.0]:
 row=[]
 for y in [0,.1,.2,.25,.3]:
  hit,loc,n,idx=o.ray_cast(Vector((2,y,z)),Vector((-1,0,0)))
  row.append([y,round(loc.x,4) if hit else None])
 out.append([z,row])
(r/'surface_samples.json').write_text(json.dumps(out,indent=2))
print('SURFACE',json.dumps(out))
