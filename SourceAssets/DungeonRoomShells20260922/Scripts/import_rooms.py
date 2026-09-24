"""Import room shell groups only; no map mutation or automatic tests."""
import json,re,sys
from pathlib import Path
import unreal as u
ROOT=Path(__file__).resolve().parents[1];BASE='/Game/Dungeons/RoomShells20260922'
sys.path.insert(0,str(ROOT.parents[1]/'Tools/AssetPipeline'))
from dungeon_material_usage import ensure_mesh_material_usage
MAN=json.loads((ROOT/'Authored/manifest.json').read_text(encoding='utf-8'))
finish_file=ROOT.parent/'DungeonSeamMetal20260923/Config/material-remap.json'
finish_receipt=ROOT.parent/'DungeonSeamMetal20260923/Receipts/install.json'
FINISH=json.loads(finish_file.read_text(encoding='utf-8')) if finish_file.exists() and finish_receipt.exists() and json.loads(finish_receipt.read_text()).get('stage')=='map_saved' else {}
wall_finish=ROOT.parent/'DungeonWallDamage20260923'
if (wall_finish/'Receipts/install.json').exists() and json.loads((wall_finish/'Receipts/install.json').read_text()).get('stage')=='map_saved':
    FINISH.update(json.loads((wall_finish/'Config/material-remap.json').read_text()))
E=u.EditorAssetLibrary;AT=u.AssetToolsHelpers.get_asset_tools()
if Path(u.Paths.project_dir()).resolve()!=ROOT.parents[1].resolve():raise RuntimeError('Different project')
if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():raise RuntimeError('Preserve running game')
if any(p.get_name().startswith(BASE+'/Meshes/') for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):raise RuntimeError('Preserve unsaved room mesh edits')
(ROOT/'Receipts').mkdir(exist_ok=True)
path=ROOT/'Receipts/import.json';receipt=json.loads(path.read_text()) if path.exists() else {'stage':'importing','meshes':{},'tests_run':False}
for item in MAN['objects']:
    if globals().get('ROOM_IDS') and item['room'] not in ROOM_IDS:continue
    previous_path=BASE+'/Meshes/'+item['name'];previous_mesh=u.load_asset(previous_path) if E.does_asset_exist(previous_path) else None
    previous_nanite=previous_mesh.get_editor_property('nanite_settings') if previous_mesh else None
    task=u.AssetImportTask();task.filename=item['fbx'];task.destination_path=BASE+'/Meshes';task.destination_name=item['name']
    task.automated=True;task.replace_existing=True;task.replace_existing_settings=True;task.save=False
    options=u.FbxImportUI();options.import_mesh=True;options.import_materials=False;options.import_textures=False;options.import_as_skeletal=False
    options.automated_import_should_detect_type=False;options.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
    data=options.static_mesh_import_data;data.combine_meshes=True;data.convert_scene=True;data.convert_scene_unit=True
    data.transform_vertex_to_absolute=True;data.auto_generate_collision=False;data.generate_lightmap_u_vs=False
    data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
    data.set_editor_property('vertex_color_import_option',u.VertexColorImportOption.REPLACE)
    task.options=options;task.factory=u.FbxFactory();AT.import_asset_tasks([task])
    asset_path=BASE+'/Meshes/'+item['name'];mesh=u.load_asset(asset_path)
    if not mesh:raise RuntimeError('Import failed '+asset_path)
    for index,slot in enumerate(mesh.get_editor_property('static_materials')):
        name=re.sub(r'[._][0-9]{3}$','',str(slot.material_slot_name))
        original=item['materials'][name]
        material=u.load_asset(FINISH.get(original.split('.')[0],original))
        if not material:raise RuntimeError('Missing source material '+item['materials'][name])
        mesh.set_material(index,material)
    ensure_mesh_material_usage(mesh)
    mesh.get_editor_property('body_setup').set_editor_property('collision_trace_flag',u.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
    if previous_nanite is not None:u.get_editor_subsystem(u.StaticMeshEditorSubsystem).set_nanite_settings(mesh,previous_nanite,True)
    if not E.save_loaded_asset(mesh,False):raise RuntimeError('Mesh save failed '+asset_path)
    receipt['meshes'][item['name']]=asset_path
    path.write_text(json.dumps(receipt,indent=2),encoding='utf-8')
receipt['stage']='meshes_saved' if len(receipt['meshes'])==len(MAN['objects']) else 'importing'
path.write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print('ROOM_SHELL_IMPORT_BATCH_SAVED',globals().get('ROOM_IDS','all'),len(receipt['meshes']))
