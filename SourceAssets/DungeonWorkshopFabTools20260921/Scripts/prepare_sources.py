"""Read downloaded FBX source geometry for scoped workshop adaptation; no rendering."""
from pathlib import Path
import bpy, json, shutil, hashlib
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path('D:/FPS3D/VaultCache/FabLibrary/Ultimate_Garage_Tools_Pack__10_Items__-_Game_Ready__FREE_-eba94efa/fbx')
for folder in ('Sources', 'Authored', 'Receipts'):
    (ROOT/folder).mkdir(parents=True, exist_ok=True)
shutil.copy2(SOURCE/'metadata', ROOT/'Sources/fab-metadata.json')
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
rows=[]
for path in sorted((SOURCE/'individual_fbx_extracted/Individual FBX').glob('*.fbx')):
    shutil.copy2(path, ROOT/'Sources'/path.name)
    before=set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=str(path), use_custom_normals=True)
    for ob in set(bpy.data.objects)-before:
        if ob.type!='MESH': continue
        points=[ob.matrix_world @ v.co for v in ob.data.vertices]
        bounds=[[min(p[i] for p in points), max(p[i] for p in points)] for i in range(3)]
        rows.append(dict(file=path.name, object=ob.name, bounds=bounds,
                         vertices=len(ob.data.vertices), polygons=len(ob.data.polygons),
                         materials=[m.name for m in ob.data.materials],
                         uv_layers=[x.name for x in ob.data.uv_layers],
                         sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
images=[dict(name=i.name, path=i.filepath, packed=bool(i.packed_file)) for i in bpy.data.images]
result=dict(source=str(SOURCE), objects=rows, images=images,
            seller='Vladyslav Chykunov', listing='https://www.fab.com/listings/eba94efa-c186-4004-83ba-d420d35f8f90',
            tests_run=False, renders_run=False)
(ROOT/'Receipts/source-inputs.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'Sources/OriginalGarageTools.blend'))
print('FAB_TOOL_SOURCE_INPUTS '+json.dumps(result))
