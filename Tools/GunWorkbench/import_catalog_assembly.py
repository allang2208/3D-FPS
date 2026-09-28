"""Import the authored catalog and publish recipes only after every mesh is saved."""
import json,re,shutil,datetime,os
from pathlib import Path
import unreal as u

P=Path('D:/FPS3D/FPSGAME');ROOT=P/'SourceAssets/GunAssemblyCatalog20260928'
if Path(u.Paths.project_dir()).resolve()!=P.resolve():raise RuntimeError('Wrong target project')
if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():raise RuntimeError('Stop PIE before importing assembly assets')
manifest=json.loads((ROOT/'manifest.json').read_text(encoding='utf-8'))['weapons']
recipes=json.loads((ROOT/'recipes.json').read_text(encoding='utf-8'))['recipes']
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools()
receipt={'saved_meshes':[],'recipes_published':False,'tests_run':False,'renders_run':False}
def record():(ROOT/'import.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
def canon(name):return re.sub(r'[._][0-9]{3}$','',str(name))
for weapon in manifest:
    for row in weapon['meshes']:
        mesh=u.load_asset(row['path']) if E.does_asset_exist(row['path']) else None
        if not mesh:
            task=u.AssetImportTask();task.filename=row['fbx'];task.destination_path=row['path'].rsplit('/',1)[0]
            task.destination_name=row['name'];task.automated=True;task.replace_existing=False;task.save=False
            options=u.FbxImportUI();options.import_mesh=True;options.import_materials=False;options.import_textures=False
            options.import_as_skeletal=False;options.automated_import_should_detect_type=False
            options.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
            data=options.static_mesh_import_data;data.combine_meshes=True;data.convert_scene=True;data.convert_scene_unit=True
            data.transform_vertex_to_absolute=True;data.auto_generate_collision=False;data.generate_lightmap_u_vs=False
            data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
            task.options=options;task.factory=u.FbxFactory();A.import_asset_tasks([task]);mesh=u.load_asset(row['path'])
        if not mesh:raise RuntimeError('Assembly import failed: '+row['path'])
        for i,slot in enumerate(mesh.get_editor_property('static_materials')):
            material_path=row['materials'].get(canon(slot.material_slot_name))
            if not material_path:raise RuntimeError('Unmapped original surface: '+str(slot.material_slot_name))
            material=u.load_asset(material_path)
            if not material:raise RuntimeError('Original surface missing: '+material_path)
            mesh.set_material(i,material)
        # Same mesh is used by the translucent placement ghost: retain regular full LOD0.
        # These are bounded, short-lived workbench actors with no collision or shadows on the ghost.
        if not E.save_loaded_asset(mesh,False):raise RuntimeError('Assembly save failed: '+row['path'])
        receipt['saved_meshes'].append(row['path']);record()
    print('ASSEMBLY_WEAPON_IMPORTED '+weapon['key']+' '+str(len(weapon['meshes'])))

catalog_path=P/'Content/ColdSteelData/gun-assembly.json'
existing=json.loads(catalog_path.read_text(encoding='utf-8-sig'))
current=existing.get('recipes',[existing] if 'id' in existing else [])
new_ids={r['id'] for r in recipes}
conflicts=[r['id'] for r in current if r['id'] in new_ids and r not in recipes]
if conflicts:raise RuntimeError('Other recipe edits found; preserved catalog: '+str(conflicts))
backup=ROOT/'Before';backup.mkdir(exist_ok=True)
if not (backup/'gun-assembly.json').exists():shutil.copy2(catalog_path,backup/'gun-assembly.json')
current=[r for r in current if r['id'] not in new_ids]+recipes
pending=catalog_path.with_name('gun-assembly.catalog-20260928.tmp')
pending.write_text(json.dumps({'recipes':current},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
os.replace(pending,catalog_path)
receipt.update({'recipes_published':True,'new_recipes':[r['id'] for r in recipes],'catalog_recipe_count':len(current),
    'completed_at':datetime.datetime.now().isoformat()});record()
print('ASSEMBLY_CATALOG_SAVED '+json.dumps({'meshes':len(receipt['saved_meshes']),'recipes':len(current),'new':len(recipes)}))
