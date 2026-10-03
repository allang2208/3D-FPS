"""Read source part transforms and write a canonical production assembly."""
import bpy,json
from pathlib import Path
from mathutils import Matrix,Vector
O=Path(__file__).resolve().parent
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(O/'Original/PitViper2011_Official.glb'))
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(O/'PitViper_Original.blend'))
conversion=Matrix.Rotation(-1.5707963267948966,4,'Z')@Matrix.Scale(.1,4)
parts=[];summary=[]
for ob in bpy.context.scene.objects:
    if ob.type!='MESH':continue
    owner=ob.parent
    while owner and not owner.name.startswith(('2011pv','919','9x19')):
        owner=owner.parent
    identity=owner.name if owner else ob.name
    xf=conversion@ob.matrix_world
    vv=[xf@v.co for v in ob.data.vertices]
    normals=[xf.to_3x3().inverted().transposed()@n.vector for n in ob.data.corner_normals]
    material=ob.data.materials[0].name if ob.data.materials else ''
    entry={'object':ob.name,'identity':identity,'material':material,
           'owner_transform':[list(row) for row in conversion@owner.matrix_world] if owner else [list(row) for row in xf],
           'origin':list(conversion@owner.matrix_world.translation) if owner else list(xf.translation),
           'verts':[list(v) for v in vv],'faces':[list(p.vertices) for p in ob.data.polygons],
           'uv':[list(l.uv) for l in ob.data.uv_layers.active.data] if ob.data.uv_layers.active else [],
           'normals':[list(n.normalized()) for n in normals]}
    parts.append(entry)
    summary.append({'object':ob.name,'identity':identity,'material':material,'vertices':len(vv),
        'min':[round(min(v[i] for v in vv),6) for i in range(3)],'max':[round(max(v[i] for v in vv),6) for i in range(3)]})
(O/'canonical_parts.json').write_text(json.dumps(parts),encoding='utf8')
(O/'canonical_summary.json').write_text(json.dumps({'conversion':'glTF -> Blender Z-up; Rz(-90deg)*0.1m/source-unit; source copper bullet diameter 0.09 units -> 9mm','parts':summary},indent=2),encoding='utf8')
print(json.dumps(summary,indent=1),flush=True)
