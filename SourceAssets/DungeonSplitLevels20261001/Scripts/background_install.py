"""Import six meshes, update the production map catalog and hard references; no generation."""
import hashlib,json,re,runpy,shutil
from pathlib import Path
import unreal as u
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parents[1]
if Path(u.Paths.project_dir()).resolve()!=PROJECT.resolve():raise RuntimeError('Wrong project')
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():raise RuntimeError('Background commandlet required')
E=u.EditorAssetLibrary
report=dict(stage='importing',assets=[],tests_run=False,generation_executed=False,editor_opened=False)
manifest=json.loads((ROOT/'Authored/manifest.json').read_text('utf-8'))
sub=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
for item in manifest['objects']:
    path=item['asset'];mesh=u.load_asset(path) if E.does_asset_exist(path) else None
    if not mesh:
        task=u.AssetImportTask();task.filename=item['fbx'];task.destination_path=path.rsplit('/',1)[0];task.destination_name=item['name']
        task.automated=True;task.replace_existing=False;task.save=False
        opts=u.FbxImportUI();opts.import_mesh=True;opts.import_materials=False;opts.import_textures=False;opts.import_as_skeletal=False
        opts.automated_import_should_detect_type=False;opts.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
        data=opts.static_mesh_import_data;data.combine_meshes=True;data.convert_scene=True;data.convert_scene_unit=True
        data.transform_vertex_to_absolute=True;data.auto_generate_collision=False;data.generate_lightmap_u_vs=False
        data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
        task.options=opts;task.factory=u.FbxFactory();u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
        mesh=u.load_asset(path)
    if not mesh:raise RuntimeError('Import failed '+path)
    for i,slot in enumerate(mesh.get_editor_property('static_materials')):
        key=re.sub(r'[._][0-9]{3}$','',str(slot.material_slot_name));mat=u.load_asset(item['materials'][key])
        if not mat:raise RuntimeError('Missing material '+key)
        mesh.set_material(i,mat)
    mesh.get_editor_property('body_setup').set_editor_property('collision_trace_flag',u.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
    settings=sub.get_lod_build_settings(mesh,0);settings.use_full_precision_u_vs=True;settings.recompute_tangents=True
    sub.set_lod_build_settings(mesh,0,settings)
    n=mesh.get_editor_property('nanite_settings').copy();n.enabled=False;mesh.set_editor_property('nanite_settings',n)
    if not E.save_loaded_asset(mesh,False):raise RuntimeError('Save failed '+path)
    report['assets'].append(path)
    (ROOT/'Receipts/install.json').write_text(json.dumps(report,indent=2),encoding='utf-8')

target='/Game/GameMaps/L_Dungeon_Randomized';source=PROJECT/'Content/GameMaps/L_Dungeon_Randomized.umap'
digest=hashlib.sha256(source.read_bytes()).hexdigest();backup=ROOT/'Backup'/f'L_Dungeon_Randomized-{digest[:12]}.umap'
if not backup.exists():shutil.copy2(source,backup)
world=u.EditorLoadingAndSavingUtils.load_map(target)
if not world:raise RuntimeError('Production map unavailable')
generators=u.GameplayStatics.get_all_actors_of_class(world,u.AuthoredDungeonGenerator)
if len(generators)!=1:raise RuntimeError('Production generator unavailable')
g=generators[0];before=g.get_editor_property('module_catalog_json')
(ROOT/'Backup'/f'catalog-{hashlib.sha256(before.encode()).hexdigest()[:12]}.json').write_text(before,encoding='utf-8')
catalog=runpy.run_path(str(ROOT/'Scripts/extend_catalog.py'))['extend'](json.loads(before))
assets={a.get_path_name():a for a in g.get_editor_property('module_assets') if a}
for item in manifest['objects']:
    for path in [item['asset'],*item['materials'].values()]:
        a=u.load_asset(path)
        if not a:raise RuntimeError('Missing dependency '+path)
        assets[a.get_path_name()]=a
g.modify();g.set_editor_property('module_catalog_json',json.dumps(catalog,ensure_ascii=False));g.set_editor_property('module_assets',list(assets.values()))
if not u.EditorLoadingAndSavingUtils.save_map(world,target):raise RuntimeError('Production map not saved')
text=json.dumps(catalog,ensure_ascii=False,indent=2)
for dest in (ROOT/'Config/catalog.json',PROJECT/'SourceAssets/DungeonThemedRoutes20261001/Config/catalog.json',PROJECT/'SourceAssets/DungeonRoutes20260922/Config/catalog.json'):
    dest.write_text(text,encoding='utf-8')
report.update(stage='map_saved',map=target,prior_map_sha256=digest,backup=str(backup),hard_dependencies=len(assets))
(ROOT/'Receipts/install.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('SPLIT_LEVEL_PRODUCTION_SAVED',flush=True)
