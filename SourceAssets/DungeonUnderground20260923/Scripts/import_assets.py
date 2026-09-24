"""Import and save only the new descent module in the owning editor/batch."""
import json,re
from pathlib import Path
import unreal as u
root=Path(__file__).resolve().parents[1]
base='/Game/Dungeons/Underground20260923/Meshes'
ue=u.get_editor_subsystem(u.UnrealEditorSubsystem)
if ue and ue.get_game_world():raise RuntimeError('Preserve active game; stair import pending')
if any(p.get_name().startswith(base) for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):
    raise RuntimeError('Preserve unsaved stair assets')
manifest=json.loads((root/'Authored/manifest.json').read_text(encoding='utf-8'))
receipt={'stage':'importing','meshes':{},'runtime_tested':False}
for item in manifest['objects']:
    task=u.AssetImportTask();task.filename=item['fbx'];task.destination_path=base;task.destination_name=item['name']
    task.automated=True;task.replace_existing=True;task.replace_existing_settings=True;task.save=False
    options=u.FbxImportUI();options.import_mesh=True;options.import_materials=False;options.import_textures=False
    options.import_as_skeletal=False;options.automated_import_should_detect_type=False
    options.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
    data=options.static_mesh_import_data;data.combine_meshes=True;data.convert_scene=True;data.convert_scene_unit=True
    data.transform_vertex_to_absolute=True;data.auto_generate_collision=False;data.generate_lightmap_u_vs=False
    data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
    data.set_editor_property('vertex_color_import_option',u.VertexColorImportOption.REPLACE)
    task.options=options;task.factory=u.FbxFactory()
    u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    path=base+'/'+item['name'];mesh=u.load_asset(path)
    if not mesh or not task.get_objects():raise RuntimeError('Stair import failed '+path)
    for i,slot in enumerate(mesh.get_editor_property('static_materials')):
        name=re.sub(r'[._][0-9]{3}$','',str(slot.material_slot_name))
        material=u.load_asset(item['materials'][name])
        if not material:raise RuntimeError('Missing inherited material '+item['materials'][name])
        mesh.set_material(i,material)
    mesh.get_editor_property('body_setup').set_editor_property('collision_trace_flag',u.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
    settings=mesh.get_editor_property('nanite_settings').copy();settings.enabled=True
    settings.explicit_tangents=True
    settings.generate_fallback=u.NaniteGenerateFallback.ENABLED
    settings.fallback_target=u.NaniteFallbackTarget.PERCENT_TRIANGLES
    settings.fallback_percent_triangles=1.0;settings.fallback_relative_error=0.0
    mesh.set_editor_property('nanite_settings',settings)
    if not u.EditorAssetLibrary.save_loaded_asset(mesh,False):raise RuntimeError('Save failed '+path)
    receipt['meshes'][item['name']]=path
receipt['stage']='meshes_saved'
(root/'Receipts/import.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print('UNDERGROUND_MESHES_SAVED',json.dumps(receipt),flush=True)
