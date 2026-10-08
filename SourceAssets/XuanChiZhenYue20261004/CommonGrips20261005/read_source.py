"""Read the current fitted grip as manufacturing input, without a preview or test."""
import bpy,json,math
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
P=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(P.parent/'SurfaceV2/XuanChi_SurfaceV2_Editable.blend'))
obj=bpy.data.objects['SM_XuanChi_Grip_V2'];mesh=obj.data
lo=min(v.co.z for v in mesh.vertices);hi=max(v.co.z for v in mesh.vertices)
bvh=BVHTree.FromPolygons([v.co for v in mesh.vertices],[list(p.vertices) for p in mesh.polygons])
sections=[]
for t in [.01,.04,.072,.10,.2,.35,.5,.65,.8,.9,.928,.96,.99]:
    z=hi+(lo-hi)*t
    points=[bvh.ray_cast(Vector((0,0,z)),Vector((math.cos(a),math.sin(a),0)),.15)[0] for a in [0,math.pi/2,math.pi,math.pi*1.5]]
    sections.append({'t':t,'z_m':z,'radii_m':[math.hypot(p.x,p.y) if p is not None else None for p in points]})
record={'object':obj.name,'length_cm':100*(hi-lo),'local_z_m':[lo,hi],
    'location_m':list(obj.location),'materials':[m.name for m in mesh.materials],
    'uvs':[uv.name for uv in mesh.uv_layers],'sections':sections}
(P/'source_inputs.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
print('XUANCHI_GRIP_MANUFACTURING_INPUT '+json.dumps(record),flush=True)
