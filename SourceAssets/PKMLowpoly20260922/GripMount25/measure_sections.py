import bpy,json
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
O=Path(__file__).parent
bpy.ops.wm.open_mainfile(filepath=str(O/'MountInspection.blend'),use_scripts=False)
def section(objects,z,material=None):
    points=[]
    for ob in objects:
        for edge in ob.data.edges:
            a,b=[ob.matrix_world@ob.data.vertices[i].co for i in edge.vertices]
            if (a.z-z)*(b.z-z)>0 or abs(b.z-a.z)<1e-9:continue
            p=a.lerp(b,(z-a.z)/(b.z-a.z));points.append(p)
    if not points:return None
    lo=[min(p[i] for p in points) for i in range(2)];hi=[max(p[i] for p in points) for i in range(2)]
    return {'min':lo,'max':hi,'center':[(a+b)/2 for a,b in zip(lo,hi)]}
factory=[bpy.data.objects['Factory_PKM_Part_'+i] for i in ['045','046']]
groups={'factory':factory}
for key,name in [('phantom_reargrip','SM_PhantomRearGrip'),('balanced_reargrip','SM_BalancedRearGrip'),('stable_antislip_reargrip','SM_StableAntiSlipRearGrip')]:groups[key]=[bpy.data.objects[name]]
out={key:{str(z):section(obs,z) for z in [.02,.01,0.,-.015,-.03,-.05,-.07]} for key,obs in groups.items()}
gas=bpy.data.objects['Factory_PKM_Part_068'];bvh=BVHTree.FromPolygons([v.co for v in gas.data.vertices],[p.vertices[:] for p in gas.data.polygons])
out['fore_seat']={str(y):{str(x):((lambda hit:list(hit[0]) if hit[0] else None)(bvh.ray_cast(Vector((x,y,-.1)),Vector((0,0,1)),.3))) for x in [0,.006,.012,.013]} for y in [-.403,-.39,-.37,-.35,-.33,-.319]}
(O/'sections.json').write_text(json.dumps(out,indent=2));print(json.dumps(out),flush=True)
