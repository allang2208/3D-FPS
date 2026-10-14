"""Reimport the shared body in place; leave room assembly and lights untouched."""
from pathlib import Path
from datetime import datetime
import json, shutil, re
import unreal as u

ROOT=Path(__file__).resolve().parent
PROJECT=ROOT.parents[2]
source=json.loads((ROOT/'Receipts/source.json').read_text('utf8'))
asset=source['asset']
if Path(u.Paths.project_dir()).resolve()!=PROJECT.resolve():raise RuntimeError('Wrong project')
editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
level=u.get_editor_subsystem(u.LevelEditorSubsystem)
if editor.get_game_world() or (level and level.is_in_play_in_editor()):
    raise RuntimeError('Cannot reimport while gameplay is active')
dirty={p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if asset in dirty:raise RuntimeError('Preserve unsaved shared bookcase asset')
mesh=u.load_asset(asset)
if not mesh:raise RuntimeError('Missing installed bookcase '+asset)

disk=PROJECT/'Content'/(asset.removeprefix('/Game/')+'.uasset')
backup=ROOT/'Backups'/('UE-'+datetime.now().strftime('%Y%m%d-%H%M%S'))
backup.mkdir(parents=True,exist_ok=True)
shutil.copy2(disk,backup/disk.name)
sub=u.get_editor_subsystem(u.StaticMeshEditorSubsystem)
build=sub.get_lod_build_settings(mesh,0).copy()
nanite=mesh.get_editor_property('nanite_settings').copy()
trace=mesh.get_editor_property('body_setup').get_editor_property('collision_trace_flag')
materials={str(s.material_slot_name):s.material_interface for s in mesh.static_materials}
collision_count=sub.get_convex_collision_count(mesh)

task=u.AssetImportTask()
task.filename=source['fbx'];task.destination_path=asset.rsplit('/',1)[0];task.destination_name=asset.rsplit('/',1)[1]
task.automated=True;task.replace_existing=True;task.replace_existing_settings=True;task.save=False
opts=u.FbxImportUI();opts.import_mesh=True;opts.import_materials=False;opts.import_textures=False;opts.import_as_skeletal=False
opts.automated_import_should_detect_type=False;opts.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
data=opts.static_mesh_import_data
data.combine_meshes=True;data.convert_scene=True;data.convert_scene_unit=True;data.transform_vertex_to_absolute=True
data.auto_generate_collision=False;data.one_convex_hull_per_ucx=True
data.generate_lightmap_u_vs=False;data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
data.normal_generation_method=u.FBXNormalGenerationMethod.MIKK_T_SPACE;data.vertex_color_import_option=u.VertexColorImportOption.REPLACE
task.options=opts;task.factory=u.FbxFactory()
world=editor.get_editor_world()
previous=u.SystemLibrary.get_console_variable_int_value('Interchange.FeatureFlags.Import.FBX')
u.SystemLibrary.execute_console_command(world,'Interchange.FeatureFlags.Import.FBX 0')
try:
    u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    mesh=u.load_asset(asset)
    if not mesh or not task.imported_object_paths:raise RuntimeError('Bookcase reimport did not complete')
    for i,slot in enumerate(mesh.static_materials):
        name=str(slot.material_slot_name)
        if name not in materials:raise RuntimeError('Unexpected material slot '+name)
        mesh.set_material(i,materials[name])
    sub.set_lod_build_settings(mesh,0,build)
    mesh.set_editor_property('nanite_settings',nanite)
    mesh.get_editor_property('body_setup').set_editor_property('collision_trace_flag',trace)
    if nanite.enabled and not u.PlazaInstanceTools.build_nanite_data(mesh):raise RuntimeError('Bookcase mesh build failed')
    if not u.EditorAssetLibrary.save_loaded_asset(mesh,False):raise RuntimeError('Bookcase save failed')
finally:
    u.SystemLibrary.execute_console_command(world,'Interchange.FeatureFlags.Import.FBX '+str(previous))

report=dict(stage='asset_saved',asset=asset,source_sha256=source['source_sha256'],
    backup=str(backup/disk.name),materials={k:v.get_path_name() if v else None for k,v in materials.items()},
    collision_hulls_before=collision_count,collision_hulls_saved=sub.get_convex_collision_count(mesh),
    nanite_enabled=nanite.enabled,maps_rebuilt=False,game_run=False,rendered=False)
(ROOT/'Receipts/install.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
# Keep the original importer's content hash aligned with the now-saved body.
old_receipt=ROOT.parent/'ScenePolishV4/install.json'
if old_receipt.exists():
    old=json.loads(old_receipt.read_text('utf8'))
    item=old.get('meshes',{}).get(asset.rsplit('/',1)[1])
    if item:
        shutil.copy2(old_receipt,backup/'scene-polish-install.json')
        item.update(source_sha256=source['source_sha256'],triangles=source['triangles'],joint_revision='20261010')
        old_receipt.write_text(json.dumps(old,ensure_ascii=False,indent=2),encoding='utf8')
print('BOOKCASE_JOINT_ASSET_SAVED',json.dumps(report,ensure_ascii=False),flush=True)
