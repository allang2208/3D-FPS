"""Save new assembly assets, then append recipes without changing paid part order."""
import json, re, shutil, os
from pathlib import Path
import unreal as u

P = Path(u.Paths.project_dir()).resolve()
ROOT = Path(globals().get('ASSEMBLY_ROOT', P / 'SourceAssets/GunAssemblyCompletion20261015'))
manifest = json.loads((ROOT/'manifest.json').read_text(encoding='utf-8'))['weapons']
recipes = json.loads((ROOT/'recipes.json').read_text(encoding='utf-8'))['recipes']
E = u.EditorAssetLibrary
receipt = {'saved_meshes': [], 'recipes_published': False, 'interactive_tested': False}
def record():
    (ROOT/'import.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding='utf-8')
def canon(name): return re.sub(r'[._][0-9]{3}$', '', str(name))

for weapon in manifest:
    for row in weapon['meshes']:
        mesh = u.load_asset(row['path']) if E.does_asset_exist(row['path']) else None
        if mesh is None:
            task = u.AssetImportTask()
            task.filename = row['fbx']; task.destination_path = row['path'].rsplit('/', 1)[0]
            task.destination_name = row['name']; task.automated = True
            task.replace_existing = False; task.save = False
            options = u.FbxImportUI(); options.import_mesh = True
            options.import_materials = False; options.import_textures = False
            options.import_as_skeletal = False; options.automated_import_should_detect_type = False
            options.mesh_type_to_import = u.FBXImportType.FBXIT_STATIC_MESH
            data = options.static_mesh_import_data
            data.combine_meshes = True; data.convert_scene = True; data.convert_scene_unit = True
            data.transform_vertex_to_absolute = True; data.auto_generate_collision = False
            data.generate_lightmap_u_vs = False
            data.normal_import_method = u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
            task.options = options; task.factory = u.FbxFactory()
            u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
            mesh = u.load_asset(row['path'])
        if not isinstance(mesh, u.StaticMesh): raise RuntimeError('Missing mesh '+row['path'])
        for i, slot in enumerate(mesh.get_editor_property('static_materials')):
            path = row['materials'].get(canon(slot.material_slot_name))
            material = u.load_asset(path) if path else None
            if material is None: raise RuntimeError('Missing original material '+str(slot.material_slot_name))
            mesh.set_material(i, material)
        if not E.save_loaded_asset(mesh, False): raise RuntimeError('Save failed '+row['path'])
        receipt['saved_meshes'].append(row['path']); record()
    print('ASSEMBLY_SAVED', weapon['key'], len(weapon['meshes']))

catalog_path = P/'Content/ColdSteelData/gun-assembly.json'
existing = json.loads(catalog_path.read_text(encoding='utf-8-sig'))
current = existing['recipes']
import sys
sys.path.insert(0,str(P/'Tools/GunWorkbench'))
from assembly_recipe_policy import preserve_gameplay_recipe
recipes = [preserve_gameplay_recipe(r,next((old for old in current if old['id']==r['id']),None)) for r in recipes]
new_ids = {r['id'] for r in recipes}
for old in current:
    if old['id'] in new_ids:
        new = next(r for r in recipes if r['id'] == old['id'])
        if old != new: raise RuntimeError('Concurrent recipe change preserved: '+old['id'])
backup = ROOT/'Before'; backup.mkdir(exist_ok=True)
if not (backup/'gun-assembly.json').exists(): shutil.copy2(catalog_path, backup/'gun-assembly.json')
current.extend(r for r in recipes if r['id'] not in {old['id'] for old in current})
# Runtime framing adapts each recipe. Appending guns must not rewrite older placements or cameras.
pending = catalog_path.with_suffix('.'+ROOT.name+'.tmp')
pending.write_text(json.dumps(existing, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
os.replace(pending, catalog_path)
receipt.update(recipes_published=True, recipe_count=len(current), added=[r['id'] for r in recipes])
record()
print('ASSEMBLY_CATALOG_PUBLISHED', len(current))
