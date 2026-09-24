"""Import the migrated solid frame and non-colliding energy surface as separate assets."""
import json
import re
from pathlib import Path
import unreal as u

HERE = Path(__file__).parent
ROOT = '/Game/Props/GamedevPortal20260922'
level_editor = u.get_editor_subsystem(u.LevelEditorSubsystem)
if level_editor.is_in_play_in_editor():
    level_editor.editor_request_end_play()
    raise RuntimeError('Requested end of PIE because asset editing requires editor mode; resume this import after PIE ends.')

def import_mesh(name):
    path = ROOT+'/'+name
    mesh = u.load_asset(path)
    if mesh is not None and u.EditorAssetLibrary.get_metadata_tag(mesh,'PortalSource') not in ['', 'gamedev_20260821']:
        raise RuntimeError('Preserve unknown mesh revision: '+path)
    if mesh is None or u.EditorAssetLibrary.get_metadata_tag(mesh,'PortalAxisVersion') != 'baked_x_forward_legacy_v5':
        if mesh is not None:
            if u.EditorAssetLibrary.get_metadata_tag(mesh,'PortalSource') != 'gamedev_20260821':
                raise RuntimeError('Cannot replace an unowned import: '+path)
            if not u.EditorAssetLibrary.delete_asset(path):
                raise RuntimeError('Cannot replace this task\'s incomplete import: '+path)
            mesh = None
        options = u.FbxImportUI()
        options.automated_import_should_detect_type = False
        options.mesh_type_to_import = u.FBXImportType.FBXIT_STATIC_MESH
        options.import_mesh = True; options.import_as_skeletal = False
        options.import_materials = False; options.import_textures = False
        data = options.static_mesh_import_data
        data.combine_meshes = True; data.auto_generate_collision = False
        data.generate_lightmap_u_vs = True; data.transform_vertex_to_absolute = True
        data.convert_scene = True; data.convert_scene_unit = True
        # The export has baked +X forward; reimport must not reuse a prior rotation.
        data.import_rotation = u.Rotator(pitch=0.0, yaw=0.0, roll=0.0)
        data.normal_import_method = u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
        task = u.AssetImportTask()
        task.set_editor_property('async_', False)
        task.filename = str(HERE/'Authored'/(name+'.fbx'))
        task.destination_path = ROOT; task.destination_name = name
        task.automated = True; task.replace_existing = mesh is not None; task.save = False
        task.replace_existing_settings = True
        task.options = options; task.factory = u.FbxFactory()
        u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
        imported = task.get_objects()
        mesh = next((obj for obj in imported if isinstance(obj,u.StaticMesh) and obj.get_path_name() == path+'.'+name),None)
        if mesh is None: raise RuntimeError('Mesh import failed: '+name)
    materials = []
    for index, slot in enumerate(mesh.get_editor_property('static_materials')):
        material_name = re.sub(r'[._][0-9]{3}$', '', str(slot.get_editor_property('material_slot_name')))
        material = u.load_asset(ROOT+'/Materials/M_'+material_name)
        if material is None: raise RuntimeError('Missing portal material: '+material_name)
        mesh.set_material(index, material)
        materials.append(material.get_path_name())
    solid = name.endswith('_Frame')
    body = mesh.get_editor_property('body_setup')
    if solid:
        body.set_editor_property('collision_trace_flag', u.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
    nanite = mesh.get_editor_property('nanite_settings')
    nanite.enabled = solid
    mesh.set_editor_property('nanite_settings', nanite)
    u.EditorAssetLibrary.set_metadata_tag(mesh,'PortalSource','gamedev_20260821')
    u.EditorAssetLibrary.set_metadata_tag(mesh,'PortalAxisVersion','baked_x_forward_legacy_v5')
    if not u.EditorLoadingAndSavingUtils.save_packages([u.load_package(path)],False):
        raise RuntimeError('Package save failed: '+path)
    box = mesh.get_bounding_box()
    final_build=u.get_editor_subsystem(u.StaticMeshEditorSubsystem).get_lod_build_settings(mesh,0)
    return {'mesh':mesh.get_path_name(), 'materials':materials, 'bounds':str(box), 'build_scale':str(final_build.build_scale3d), 'saved':True}

# The legacy factory honors the explicit centimetre conversion on reimport.
# Limit the global switch to this bridge-serialized import and restore it immediately.
flag = 'Interchange.FeatureFlags.Import.FBX'
previous = u.SystemLibrary.get_console_variable_int_value(flag)
world = u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
assets = []
try:
    u.SystemLibrary.execute_console_command(world, flag+' 0')
    for name in ['SM_GamedevPortal_Frame', 'SM_GamedevPortal_Energy']:
        assets.append(import_mesh(name))
finally:
    u.SystemLibrary.execute_console_command(world, flag+' '+str(previous))
(HERE/'mesh_receipt.json').write_text(json.dumps({'assets':assets,'runtime_tested':False},indent=2),encoding='utf-8')
print('PORTAL_MESHES_SAVED '+json.dumps(assets))
