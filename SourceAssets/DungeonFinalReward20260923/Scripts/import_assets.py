"""Import the final-room variants without replacing the accepted freight/Boss assets."""
import json
import re
from pathlib import Path
import unreal as u

ROOT=Path(__file__).resolve().parents[1]
PROJECT=ROOT.parents[1]
BASE='/Game/Dungeons/FinalReward20260923/Meshes'
if Path(u.Paths.project_dir()).resolve()!=PROJECT.resolve():
    raise RuntimeError('Unexpected Unreal project')
editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
if editor and editor.get_game_world():
    raise RuntimeError('Preserve active game; final-room import pending')
if any(p.get_name().startswith(BASE+'/') for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):
    raise RuntimeError('Preserve unsaved final-room assets')
manifest=json.loads((ROOT/'Authored/manifest.json').read_text(encoding='utf-8'))
receipt=dict(stage='importing',meshes={},runtime_tested=False,rendered=False)
receipt_path=ROOT/'Receipts/import.json'

def record():receipt_path.write_text(json.dumps(receipt,indent=2),encoding='utf-8')

record()
for item in manifest['objects']:
    task=u.AssetImportTask();task.filename=item['fbx']
    task.destination_path=BASE;task.destination_name=item['name']
    task.automated=True;task.replace_existing=True;task.replace_existing_settings=True;task.save=False
    options=u.FbxImportUI();options.import_mesh=True;options.import_materials=False;options.import_textures=False
    options.import_as_skeletal=False;options.automated_import_should_detect_type=False
    options.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
    data=options.static_mesh_import_data
    data.combine_meshes=True;data.convert_scene=True;data.convert_scene_unit=True
    data.transform_vertex_to_absolute=True;data.auto_generate_collision=False;data.generate_lightmap_u_vs=False
    data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
    data.vertex_color_import_option=u.VertexColorImportOption.REPLACE
    task.options=options;task.factory=u.FbxFactory()
    u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    path=BASE+'/'+item['name'];mesh=u.load_asset(path)
    if not mesh or not task.get_objects():raise RuntimeError('Final-room import failed '+path)
    for index,slot in enumerate(mesh.get_editor_property('static_materials')):
        key=re.sub(r'[._][0-9]{3}$','',str(slot.material_slot_name))
        material=u.load_asset(item['materials'][key])
        if not material:raise RuntimeError('Missing inherited material '+item['materials'][key])
        mesh.set_material(index,material)
    body=mesh.get_editor_property('body_setup')
    body.set_editor_property('collision_trace_flag',u.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
    settings=mesh.get_editor_property('nanite_settings').copy()
    settings.enabled=True;settings.explicit_tangents=True
    settings.generate_fallback=u.NaniteGenerateFallback.ENABLED
    settings.fallback_target=u.NaniteFallbackTarget.PERCENT_TRIANGLES
    settings.fallback_percent_triangles=1.0;settings.fallback_relative_error=0.0
    mesh.set_editor_property('nanite_settings',settings)
    if not u.EditorAssetLibrary.save_loaded_asset(mesh,False):raise RuntimeError('Save failed '+path)
    receipt['meshes'][item['name']]=path;record()
receipt['stage']='meshes_saved';record()
print('FINAL_REWARD_MESHES_SAVED',len(receipt['meshes']),flush=True)
