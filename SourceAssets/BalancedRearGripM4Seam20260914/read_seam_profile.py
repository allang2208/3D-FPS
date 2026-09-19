"""Sample mating surfaces as construction inputs for the new bridge."""
import bpy,json
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
P=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(P/'Seam_Authoring_Source.blend'))
grip=bpy.data.objects['SM_BalancedRearGrip'];receiver=bpy.data.objects['Receiver_M4_M4 Body_Export']
def bvh(ob,body_only=False):
    faces=[tuple(f.vertices) for f in ob.data.polygons if not body_only or 'Collar' not in ob.data.materials[f.material_index].name]
    return BVHTree.FromPolygons([ob.matrix_world@v.co for v in ob.data.vertices],faces)
g=bvh(grip,True);r=bvh(receiver);out=[]
for iy in range(-28,41,3):
    y=iy/1000;row={'y_mm':iy,'samples':[]}
    for ix in [-13,-10,-7,0,7,10,13]:
        x=ix/1000;hit=g.ray_cast(Vector((x,y,.055)),Vector((0,0,-1)),.12)[0]
        rhit=r.ray_cast(Vector((x,y,-.015)),Vector((0,0,1)),.11)[0]
        row['samples'].append([ix,round(hit.z*1000,3) if hit else None,round(rhit.z*1000,3) if rhit else None])
    out.append(row)
(P/'seam_profile.json').write_text(json.dumps(out,indent=2))
