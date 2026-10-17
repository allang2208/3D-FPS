"""Save fitted M870 devices with the donor materials and authored emitter sockets."""
import json,re
from pathlib import Path
import unreal as u

O=Path(__file__).parent;D='/Game/Weapons/M870/TacticalFit20261017'
data=json.loads((O/'authoring.json').read_text())
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
    if u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():raise RuntimeError('Stop PIE before saving tactical meshes')
dirty={p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if any(p.startswith(D+'/') for p in dirty):raise RuntimeError('Preserve unsaved M870 tactical assets')
flag='Interchange.FeatureFlags.Import.FBX';old=u.SystemLibrary.get_console_variable_int_value(flag)
u.SystemLibrary.execute_console_command(None,flag+' 0')
R={'saved':{},'completed':False,'runtime_tested':False}
def clean(s):return re.sub(r'[._]\d{3}$','',s)
try:
    for kind,e in data['devices'].items():
        opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
        opt.import_mesh=True;opt.import_materials=False;opt.import_textures=False;opt.import_animations=False
        sm=opt.static_mesh_import_data;sm.combine_meshes=True;sm.auto_generate_collision=False;sm.generate_lightmap_u_vs=False
        sm.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
        sm.vertex_color_import_option=u.VertexColorImportOption.REPLACE
        task=u.AssetImportTask();task.filename=e['fbx'];task.destination_path=D;task.destination_name='SM_'+kind
        task.automated=True;task.replace_existing=True;task.replace_existing_settings=True;task.save=False;task.options=opt;task.factory=u.FbxFactory()
        u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
        mesh=u.load_asset(D+'/'+task.destination_name)
        if not mesh:raise RuntimeError('Missing import '+kind)
        bindings={clean(k):v for k,v in e['materials'].items()};slots=list(mesh.static_materials)
        for i,slot in enumerate(slots):
            label=clean(str(slot.get_editor_property('imported_material_slot_name')))
            path=bindings.get(label)
            if not path:raise RuntimeError('Unbound tactical material '+label)
            mat=u.load_asset(path)
            if not mat:raise RuntimeError('Missing tactical material '+path)
            slot.material_interface=mat;slots[i]=slot
        mesh.set_editor_property('static_materials',slots)
        donor=u.load_asset(e['source']);mesh.set_editor_property('nanite_settings',donor.get_editor_property('nanite_settings'))
        u.ASH12AttachmentAssetTools.disable_runtime_fast_build(mesh)
        editor=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
        settings=editor.get_lod_build_settings(mesh,0);settings.recompute_normals=False;settings.recompute_tangents=False
        settings.use_high_precision_tangent_basis=True;settings.use_full_precision_u_vs=True;editor.set_lod_build_settings(mesh,0,settings)
        for name,pos in e['sockets'].items():
            socket=mesh.find_socket(name)
            if socket is None:
                socket=u.StaticMeshSocket(outer=mesh);socket.set_editor_property('socket_name',name);mesh.add_socket(socket)
            socket.set_editor_property('relative_location',u.Vector(*pos));socket.set_editor_property('relative_rotation',u.Rotator())
        u.EditorAssetLibrary.set_metadata_tag(mesh,'M870TacticalMount','Fixed magazine tube clamp; component seat (0,-35.5,-80.5) cm; +X optical axis; WPN_root')
        u.EditorAssetLibrary.set_metadata_tag(mesh,'SourceDevice',e['source'])
        if not u.EditorAssetLibrary.save_loaded_asset(mesh,False):raise RuntimeError('Save failed '+kind)
        R['saved'][kind]=mesh.get_path_name();(O/'import_receipt.json').write_text(json.dumps(R,indent=2))
        print('M870_TACTICAL_SAVED '+kind,flush=True)
    R['completed']=True;(O/'import_receipt.json').write_text(json.dumps(R,indent=2))
finally:u.SystemLibrary.execute_console_command(None,flag+' '+str(old))
