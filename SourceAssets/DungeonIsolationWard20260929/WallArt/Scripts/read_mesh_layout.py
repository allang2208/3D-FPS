"""Extract original atlas islands, face direction and bounds for placement authoring."""
import json
from pathlib import Path
import bpy
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1]
records=json.loads((ROOT/'sources.json').read_text(encoding='utf-8'))
for entry in records:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=entry['fbx'])
    objects=[o for o in bpy.context.scene.objects if o.type=='MESH']
    verts=[];uvs=[];normals=[]
    for obj in objects:
        verts.extend(obj.matrix_world@v.co for v in obj.data.vertices)
        normals.extend(obj.matrix_world.to_3x3()@p.normal for p in obj.data.polygons)
        uvs.extend(v.uv.copy() for v in obj.data.uv_layers[0].data)
    entry['blender_min']=[min(v[k] for v in verts) for k in range(3)]
    entry['blender_max']=[max(v[k] for v in verts) for k in range(3)]
    entry['normal_blender']=list(sum(normals,Vector()).normalized())
    entry['uv_min']=[min(v[k] for v in uvs) for k in range(2)]
    entry['uv_max']=[max(v[k] for v in uvs) for k in range(2)]
(ROOT/'source_geometry.json').write_text(json.dumps(records,indent=2),encoding='utf-8')
print('WARD_POSTER_GEOMETRY_READ',len(records))
