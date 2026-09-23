"""Import the one authored connector with its existing material family and solid collision."""
import unreal as u,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];BASE='/Game/Dungeons/DoorTransitions20260922/Meshes'
if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():raise RuntimeError('Preserve running game')
if any(p.get_name().startswith(BASE) for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):raise RuntimeError('Preserve unsaved transition mesh')
for item in json.loads((ROOT/'Authored/manifest.json').read_text())['objects']:
    task=u.AssetImportTask();task.filename=item['fbx'];task.destination_path=BASE;task.destination_name=item['name']
    task.automated=True;task.replace_existing=True;task.replace_existing_settings=True;task.save=False
    options=u.FbxImportUI();options.import_mesh=True;options.import_materials=False;options.import_textures=False;options.import_as_skeletal=False
    options.automated_import_should_detect_type=False;options.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
    data=options.static_mesh_import_data;data.combine_meshes=True;data.convert_scene=True;data.convert_scene_unit=True
    data.transform_vertex_to_absolute=True;data.auto_generate_collision=False;data.generate_lightmap_u_vs=False
    data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
    task.options=options;task.factory=u.FbxFactory();u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    mesh=u.load_asset(BASE+'/'+item['name'])
    if not mesh:raise RuntimeError('Transition import failed')
    for index,slot in enumerate(mesh.get_editor_property('static_materials')):
        name=re.sub(r'[._][0-9]{3}$','',str(slot.material_slot_name));material=u.load_asset(item['materials'][name])
        if not material:raise RuntimeError('Missing transition material '+name)
        mesh.set_material(index,material)
    mesh.get_editor_property('body_setup').set_editor_property('collision_trace_flag',u.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
    if not u.EditorAssetLibrary.save_loaded_asset(mesh,False):raise RuntimeError('Transition save failed')
print('START_TRANSITION_ASSET_SAVED')
