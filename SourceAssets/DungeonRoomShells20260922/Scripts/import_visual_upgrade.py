"""Reimport only detailed groups, keeping room actors, transforms and lights intact."""
import json,re
from pathlib import Path
import unreal as u
ROOT=Path(__file__).resolve().parents[1];BASE='/Game/Dungeons/RoomShells20260922'
MAN=json.loads((ROOT/'Authored/manifest.json').read_text(encoding='utf-8'))
E=u.EditorAssetLibrary;AT=u.AssetToolsHelpers.get_asset_tools()
if Path(u.Paths.project_dir()).resolve()!=ROOT.parents[1].resolve():raise RuntimeError('Different project')
if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():raise RuntimeError('Play is active; end play before importing')
selected=[m for m in MAN['objects'] if m['kind'] in ('Tiles','Services','Frames','Debris') or (m['room']=='ShoredBreach' and m['kind']=='Shell')]
if globals().get('ROOM_IDS'):selected=[m for m in selected if m['room'] in ROOM_IDS]
receipt_path=ROOT/'Receipts/visual-upgrade.json'
receipt=json.loads(receipt_path.read_text()) if receipt_path.exists() else dict(stage='importing',meshes={},tests_run=False,actors_rebuilt=False,source='Authored/corridor-surface-reuse.json')
dirty_before={p.get_name() for p in list(u.EditorLoadingAndSavingUtils.get_dirty_content_packages())+list(u.EditorLoadingAndSavingUtils.get_dirty_map_packages())}
for item in selected:
    asset_path=BASE+'/Meshes/'+item['name']
    if item['name'] in receipt['meshes']:continue
    if asset_path in dirty_before:raise RuntimeError('Preserve unsaved mesh '+asset_path)
    task=u.AssetImportTask();task.filename=item['fbx'];task.destination_path=BASE+'/Meshes';task.destination_name=item['name']
    task.automated=True;task.replace_existing=True;task.replace_existing_settings=True;task.save=False
    options=u.FbxImportUI();options.import_mesh=True;options.import_materials=False;options.import_textures=False;options.import_as_skeletal=False
    options.automated_import_should_detect_type=False;options.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
    data=options.static_mesh_import_data;data.combine_meshes=True;data.convert_scene=True;data.convert_scene_unit=True
    data.transform_vertex_to_absolute=True;data.auto_generate_collision=False;data.generate_lightmap_u_vs=False
    data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
    data.set_editor_property('vertex_color_import_option',u.VertexColorImportOption.REPLACE)
    task.options=options;task.factory=u.FbxFactory();AT.import_asset_tasks([task])
    if not task.imported_object_paths:raise RuntimeError('No imported object '+asset_path)
    mesh=u.load_asset(asset_path)
    for index,slot in enumerate(mesh.get_editor_property('static_materials')):
        name=re.sub(r'[._][0-9]{3}$','',str(slot.material_slot_name))
        material=u.load_asset(item['materials'][name])
        if not material:raise RuntimeError('Missing existing material '+item['materials'][name])
        mesh.set_material(index,material)
    mesh.get_editor_property('body_setup').set_editor_property('collision_trace_flag',u.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
    if not E.save_loaded_asset(mesh,False):raise RuntimeError('Mesh save failed '+asset_path)
    receipt['meshes'][item['name']]=asset_path
    receipt_path.write_text(json.dumps(receipt,indent=2),encoding='utf-8')
new_owned=[p for p in list(u.EditorLoadingAndSavingUtils.get_dirty_content_packages())+list(u.EditorLoadingAndSavingUtils.get_dirty_map_packages()) if p.get_name() not in dirty_before and '/gamemaps/l_dungeon_authoredexpansion' in p.get_name().lower()]
if new_owned and not u.EditorLoadingAndSavingUtils.save_packages(new_owned,False):raise RuntimeError('Owned package save failed')
receipt['stage']='assets_saved' if len(receipt['meshes'])==15 else 'importing'
receipt['saved_owned_packages']=receipt.get('saved_owned_packages',0)+len(new_owned)
receipt_path.write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print('ROOM_VISUAL_UPGRADE_SAVED',globals().get('ROOM_IDS','all'),len(receipt['meshes']),receipt['stage'])
