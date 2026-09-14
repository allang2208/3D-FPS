import bpy, json
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
O=Path(__file__).parent
try:bpy.ops.wm.open_mainfile(filepath=str(O.parent/'DanWesson715MetalFinish20260914/DanWesson715_MetalFinish_Editable.blend'))
except RuntimeError as error:
    if 'Missing library override hierarchy root data' not in str(error):raise
rig=bpy.data.objects['SK_DW715_Manny'];root=rig.data.bones['WPN_root'].matrix_local;inv=root.inverted()
result={'bones':{},'parts':{},'contacts':{}}
for b in rig.data.bones:
    if b.name in ['WPN_root','WPN_FrontSight','WPN_RearSight','WPN_SOCKET_Muzzle']:
        result['bones'][b.name]={'root_position_m':list(inv@b.head_local),'matrix':[list(row) for row in b.matrix_local]}
vertices=[];faces=[]
for name in ['DW715_Frame','DW715_BarrelShroud','DW715_Cylinder_144','DW715_RearSight','DW715_FrontBlade']:
    ob=bpy.data.objects[name];points=[inv@v.co for v in ob.data.vertices]
    result['parts'][name]={'min':[min(p[i] for p in points) for i in range(3)],'max':[max(p[i] for p in points) for i in range(3)]}
    if name in ['DW715_Frame','DW715_BarrelShroud']:
        offset=len(vertices);vertices+=points;faces.extend([[v+offset for v in p.vertices] for p in ob.data.polygons])
surface=BVHTree.FromPolygons(vertices,faces)
for y in [-.04,-.06,-.08,-.10,-.12,-.14,-.16]:
    row=[]
    for x in [0,.005,.009]:
        upper=surface.ray_cast(Vector((x,y,.15)),Vector((0,0,-1)),.3)[0]
        lower=surface.ray_cast(Vector((x,y,-.15)),Vector((0,0,1)),.3)[0]
        row.append(dict(x=x,top=upper.z if upper else None,bottom=lower.z if lower else None))
    result['contacts'][str(y)]=row
(O/'mount_source.json').write_text(json.dumps(result,indent=2))
print('DW715_MOUNT_SOURCE_READ',flush=True)
