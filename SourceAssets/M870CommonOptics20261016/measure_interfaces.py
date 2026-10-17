import bpy,json
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
O=Path(__file__).parent
R={}
for key in ('holographic','eoth_holographic','panoramic_red_dot','prism_scope_2x','lpvo_1_6x','thermal_scope'):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(O/'Input'/(key+'.fbx')),use_anim=False)
    vertices=[];faces=[]
    for ob in bpy.context.scene.objects:
        if ob.type!='MESH':continue
        start=len(vertices)
        vertices.extend(tuple(ob.matrix_world@v.co) for v in ob.data.vertices)
        faces.extend(tuple(start+i for i in f.vertices) for f in ob.data.polygons)
    tree=BVHTree.FromPolygons(vertices,faces)
    R[key]={'bounds_m':[[min(v[i] for v in vertices) for i in range(3)],[max(v[i] for v in vertices) for i in range(3)]],'sections':{}}
    for x in (-.020,-.010,.010):
        rows=[]
        for y in (-.021,-.018,-.014,-.011,-.010,-.009,-.008,-.006,0,.006,.008,.009,.010,.011,.014,.018,.021):
            hit=tree.ray_cast(Vector((x,y,-.02)),Vector((0,0,1)),.04)[0]
            rows.append([y,round(hit.z,6) if hit else None])
        R[key]['sections'][str(x)]=rows
(O/'interfaces.json').write_text(json.dumps(R,indent=2))
print('M870_SIX_INTERFACE_SECTIONS_CAPTURED',flush=True)
