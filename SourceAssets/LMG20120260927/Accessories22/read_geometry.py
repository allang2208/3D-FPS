import bpy,json
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion
O=Path(__file__).parent;d=json.loads((O/'sources.json').read_text())
def bound(points):return {'min':[min(v[i] for v in points) for i in range(3)],'max':[max(v[i] for v in points) for i in range(3)]}
out={}
for key,info in d['meshes'].items():
    bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.fbx(filepath=info['file'])
    groups={}
    for ob in bpy.context.scene.objects:
        if ob.type!='MESH':continue
        for i,mat in enumerate(ob.data.materials):
            points=[ob.matrix_world@ob.data.vertices[j].co for p in ob.data.polygons if p.material_index==i for j in p.vertices]
            if points:groups[mat.name]=bound(points)
    out[key]=groups
(O/'geometry_source_bounds.json').write_text(json.dumps(out,indent=2))
print('SOURCE_GEOMETRY_READ')
