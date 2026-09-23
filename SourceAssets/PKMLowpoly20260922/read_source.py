import bpy, json, pathlib, hashlib, shutil
from mathutils import Vector

ROOT = pathlib.Path(__file__).parent
SRC = pathlib.Path('D:/FPS3D/资产/pkm_machine_gun.glb')
(ROOT / 'Original').mkdir(parents=True, exist_ok=True)
shutil.copy2(SRC, ROOT / 'Original' / SRC.name)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(SRC), merge_vertices=True)
parts=[]
for i,o in enumerate(x for x in bpy.context.scene.objects if x.type=='MESH'):
    coords=[o.matrix_world @ v.co for v in o.data.vertices]
    lo=[min(v[a] for v in coords) for a in range(3)]
    hi=[max(v[a] for v in coords) for a in range(3)]
    o['source_name']=o.name
    o['source_parent']=o.parent.name if o.parent else ''
    o.name='PKM_Source_%03d'%i
    parts.append(dict(id=i,name=o['source_name'],parent=o['source_parent'],bounds=[lo,hi],vertices=len(o.data.vertices),triangles=sum(len(p.vertices)-2 for p in o.data.polygons),materials=[m.name for m in o.data.materials],custom_normals=o.data.has_custom_normals))
report=dict(source=str(SRC),sha256=hashlib.sha256(SRC.read_bytes()).hexdigest(),parts=parts)
(ROOT/'source_structure.json').write_text(json.dumps(report,ensure_ascii=True,indent=2),encoding='utf-8')
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'Original'/'PKM_Source.blend'))
print('SOURCE_PARTS',len(parts))
for p in parts:
    if p['id']<42:continue
    print(p['id'],p['parent'].encode('ascii','replace').decode(),p['materials'], 'bounds',[[round(x,4) for x in row] for row in p['bounds']],p['triangles'])
