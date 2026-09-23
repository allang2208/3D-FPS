"""Reimport only the six owned expansion connection meshes."""
import json,re
from pathlib import Path
import unreal as u
ROOT=Path(__file__).resolve().parents[1]
MAN=json.loads((ROOT/'Authored/connections.json').read_text(encoding='utf-8'))
BASE='/Game/Dungeons/AuthoredExpansion20260922'
E=u.EditorAssetLibrary;AT=u.AssetToolsHelpers.get_asset_tools()
UE=u.get_editor_subsystem(u.UnrealEditorSubsystem)
ED=u.get_editor_subsystem(u.LevelEditorSubsystem)
if UE.get_game_world():raise RuntimeError('Preserve running game')
receipt=json.loads((ROOT/'Receipts/assembly.json').read_text(encoding='utf-8'))
def write(): (ROOT/'Receipts/assembly.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
def save(a):
    if not E.save_loaded_asset(a,False):raise RuntimeError('Save failed: '+a.get_path_name())
for item in MAN:
    task=u.AssetImportTask();task.filename=item['fbx'];task.destination_path=BASE+'/Meshes';task.destination_name=item['name']
    task.automated=True;task.replace_existing=True;task.replace_existing_settings=True;task.save=False
    options=u.FbxImportUI();options.import_mesh=True;options.import_materials=False;options.import_textures=False;options.import_as_skeletal=False
    options.automated_import_should_detect_type=False;options.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
    data=options.static_mesh_import_data;data.combine_meshes=True;data.convert_scene=True;data.convert_scene_unit=True
    data.transform_vertex_to_absolute=True;data.auto_generate_collision=False;data.generate_lightmap_u_vs=False
    data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
    data.set_editor_property('vertex_color_import_option',u.VertexColorImportOption.REPLACE)
    task.options=options;task.factory=u.FbxFactory();AT.import_asset_tasks([task])
    path=BASE+'/Meshes/'+item['name'];mesh=u.load_asset(path)
    if not mesh:raise RuntimeError('Import failed: '+path)
    for index,slot in enumerate(mesh.get_editor_property('static_materials')):
        name=re.sub(r'[._][0-9]{3}$','',str(slot.get_editor_property('material_slot_name')))
        material=u.load_asset(item['materials'][name]);mesh.set_material(index,material)
    mesh.get_editor_property('body_setup').set_editor_property('collision_trace_flag',u.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
    save(mesh);receipt['assets'][item['name']]=path
write()

receipt['opening_fix']={'method':'uv_preserving_surface_aperture_clipping','assets_imported':len(MAN),'saved':True}
write()
print('CONNECTION_MESHES_REIMPORTED_AND_SAVED',len(MAN))
dirty_maps=[p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_map_packages()]
if not dirty_maps:
    if not ED.load_level('/Game/GameMaps/L_Dungeon_AuthoredExpansion'):raise RuntimeError('Cannot open saved expansion')
else:
    print('PRESERVED_DIRTY_MAPS',dirty_maps)
