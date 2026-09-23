import bpy,json,math
from pathlib import Path
from mathutils.bvhtree import BVHTree
O=Path(__file__).parent;R=O.parent
bpy.ops.wm.open_mainfile(filepath=str(O/'PKM_Bipod_Editable.blend'),use_scripts=False)
def tree(ob):
    return BVHTree.FromPolygons([ob.matrix_world@v.co for v in ob.data.vertices],[list(p.vertices) for p in ob.data.polygons])
legs=[]
for angle in [-6,0,6]:
    for ob in [o for o in bpy.context.scene.objects if o.name.startswith(('PKM26_LegA','PKM26_LegB'))]:
        ob.rotation_euler.x=math.radians(angle);bpy.context.view_layer.update();legs.append(tree(ob))
out={}
for key in ['vertical','tactical_vertical','canted','prism','angled']:
    with bpy.data.libraries.load(str(R/'GripMount25'/f'SM_PKM_{key}.blend'),link=False) as (src,dst):dst.objects=src.objects
    counts=[]
    for ob in dst.objects:
        if ob.type=='MESH':counts.append({'part':ob.name,'intersecting_face_pairs':[len(tree(ob).overlap(leg)) for leg in legs]})
    out[key]=counts
(O/'grip_clearance_down.json').write_text(json.dumps(out,indent=2));print(json.dumps(out))
