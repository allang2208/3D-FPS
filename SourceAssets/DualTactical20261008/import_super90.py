"""Import and save task-owned Super90 devices without opening an editor UI."""
import json,re
from pathlib import Path
import unreal as u
O=Path(__file__).parent;D='/Game/Weapons/Super90/Tactical20261008'
A=u.AssetToolsHelpers.get_asset_tools();E=u.EditorAssetLibrary
entries=json.loads((O/'authoring.json').read_text())['super90']
targets={D+'/SM_Super90_'+kind for kind in entries}
dirty={p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if targets.intersection(dirty):raise RuntimeError('Unsaved edits in task destination; preserve editor state.')
bindings={'M_ASH12_GripMetal_Coat':'/Game/Weapons/ASH12/UniversalAttachments20260919/Materials/M_ASH12_GripMetal_Coat',
    'Super90_Tactical_Seat':'/Game/Weapons/ASH12/UniversalAttachments20260919/Materials/M_ASH12_GripMetal_Coat'}
for kind in ('laser','flashlight'):bindings['M_ASH12_'+kind+'_Body']='/Game/Weapons/ASH12/TacticalDevices20260920/Materials/M_ASH12_'+kind+'_Body'
for name in ('Blessed_Graphite','Blessed_Gold','Blessed_Black','Blessed_Optic','Blessed_Aperture'):
    bindings[name]='/Game/Weapons/TacticalDevices20260913/BlessedLaser20261006/Materials/M_'+name
report={'saved':[],'game_tested':False};receipt=O/'import-receipt.json'
old=u.SystemLibrary.get_console_variable_int_value('Interchange.FeatureFlags.Import.FBX')
u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
try:
    for kind,entry in entries.items():
        name='SM_Super90_'+kind;path=D+'/'+name
        options=u.FbxImportUI();options.automated_import_should_detect_type=False;options.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
        options.import_mesh=True;options.import_materials=False;options.import_textures=False;options.import_animations=False;options.override_full_name=True
        data=options.static_mesh_import_data;data.combine_meshes=True;data.auto_generate_collision=False;data.generate_lightmap_u_vs=False
        data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
        task=u.AssetImportTask();task.filename=entry['fbx'];task.destination_path=D;task.destination_name=name
        task.automated=True;task.replace_existing=True;task.replace_existing_settings=True;task.save=False;task.options=options;task.factory=u.FbxFactory()
        A.import_asset_tasks([task]);mesh=u.load_asset(path)
        if not task.imported_object_paths or mesh is None:raise RuntimeError('No imported mesh '+path)
        slots=list(mesh.static_materials)
        for i,slot in enumerate(slots):
            key=re.sub(r'[._]\d{3}$','',str(slot.material_slot_name));mat=u.load_asset(bindings[key])
            if not mat:raise RuntimeError('Missing inherited material '+key)
            slot.material_interface=mat;slots[i]=slot
        mesh.set_editor_property('static_materials',slots)
        for label,position in entry['sockets_ue_cm'].items():
            socket=mesh.find_socket(label)
            if socket is None:
                socket=u.StaticMeshSocket(outer=mesh);socket.set_editor_property('socket_name',label);mesh.add_socket(socket)
            socket.set_editor_property('relative_location',u.Vector(*position))
        E.set_metadata_tag(mesh,'SourceDevice',entry['source'])
        E.set_metadata_tag(mesh,'Mount','Native fore-end elliptical side bearing; runtime opposite roll; no negative scale')
        if not u.EditorLoadingAndSavingUtils.save_packages([mesh.get_outermost()],False):raise RuntimeError('Save failed '+path)
        report['saved'].append(mesh.get_path_name());receipt.write_text(json.dumps(report,indent=2),encoding='utf-8')
        print('DUAL_TACTICAL_SAVED '+mesh.get_path_name(),flush=True)
finally:u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX '+str(old))
report['status']='three_assets_imported_and_saved';receipt.write_text(json.dumps(report,indent=2),encoding='utf-8')
