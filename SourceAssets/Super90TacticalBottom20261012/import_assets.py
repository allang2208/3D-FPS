"""Save the three underside assemblies in their own production asset directory."""
import json,re
from pathlib import Path
import unreal as u
O=Path(__file__).parent
D='/Game/Weapons/Super90/TacticalBottom20261012'
data=json.loads((O/'authoring.json').read_text())
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
    if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():
        raise RuntimeError('Stop PIE before saving the three Super90 underside assets.')
dirty={p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if any(D+'/SM_'+kind in dirty for kind in data['devices']):raise RuntimeError('Destination has unsaved editor edits.')
old=u.SystemLibrary.get_console_variable_int_value('Interchange.FeatureFlags.Import.FBX')
u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
report={'saved':{},'runtime_tested':False}
def clean(s):return re.sub(r'[._]\d{3}$','',s)
try:
    for kind,e in data['devices'].items():
        options=u.FbxImportUI();options.automated_import_should_detect_type=False
        options.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
        options.import_mesh=True;options.import_materials=False;options.import_textures=False
        options.import_animations=False;options.override_full_name=True
        sm=options.static_mesh_import_data;sm.combine_meshes=True;sm.auto_generate_collision=False
        sm.generate_lightmap_u_vs=False;sm.remove_degenerates=False
        sm.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
        name='SM_'+kind
        task=u.AssetImportTask();task.filename=e['fbx'];task.destination_path=D;task.destination_name=name
        task.automated=True;task.replace_existing=True;task.replace_existing_settings=True
        task.save=False;task.options=options;task.factory=u.FbxFactory()
        u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
        mesh=u.load_asset(D+'/'+name)
        if mesh is None or not task.imported_object_paths:raise RuntimeError('Import failed '+name)
        bindings={clean(k):v for k,v in e['materials'].items() if v}
        slots=list(mesh.static_materials)
        for i,slot in enumerate(slots):
            label=clean(str(slot.material_slot_name));path=bindings.get(label)
            if label=='Tactical_Fitted_Bearing':
                path='/Game/Weapons/TacticalDevices20260913/BlessedLaser20261006/Materials/M_Blessed_Graphite' if kind=='blessed_laser' else '/Game/Weapons/ASH12/UniversalAttachments20260919/Materials/M_ASH12_GripMetal_Coat'
            if not path:raise RuntimeError('No material binding '+label)
            mat=u.load_asset(path)
            if mat is None:raise RuntimeError('Missing material '+path)
            slot.material_interface=mat;slots[i]=slot
        mesh.set_editor_property('static_materials',slots)
        for label,pos in e['sockets'].items():
            socket=mesh.find_socket(label)
            if socket is None:
                socket=u.StaticMeshSocket(outer=mesh);socket.set_editor_property('socket_name',label);mesh.add_socket(socket)
            socket.set_editor_property('relative_location',u.Vector(*pos))
        u.EditorAssetLibrary.set_metadata_tag(mesh,'TacticalMount','Single underside mount; native seat (0,-32,-84) cm; optical axis +X')
        u.EditorAssetLibrary.set_metadata_tag(mesh,'SourceDevice',e['source'])
        if not u.EditorLoadingAndSavingUtils.save_packages([mesh.get_outermost()],False):raise RuntimeError('Save failed '+name)
        report['saved'][kind]=mesh.get_path_name()
        (O/'imported.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
        print('SUPER90_UNDERSIDE_SAVED '+mesh.get_path_name(),flush=True)
finally:
    u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX '+str(old))
