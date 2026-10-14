"""Import the 66 task-owned fitted meshes; preserve source material and sockets."""
import json,re
from pathlib import Path
import unreal as u
O=Path(__file__).parent;D='/Game/Weapons/TacticalDevices20260913/DualFit20261008'
entries=json.loads((O/'Repaired/manifest.json').read_text())
sources=json.loads((O/'current-assets.json').read_text())['families']
A=u.AssetToolsHelpers.get_asset_tools();E=u.EditorAssetLibrary
targets={D+'/'+e['family']+f'/SM_{e["kind"]}_{e["side"]}' for e in entries.values()}
dirty={p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if targets.intersection(dirty):raise RuntimeError('Unsaved destination edits; preserve editor state.')
receipt=O/'import-receipt.json';report=json.loads(receipt.read_text()) if receipt.exists() else {'saved':{},'game_tested':False}
def clean(s):return re.sub(r'[._]\d{3}$','',s)
old=u.SystemLibrary.get_console_variable_int_value('Interchange.FeatureFlags.Import.FBX')
u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
try:
    for key,entry in entries.items():
        if entry['family']=='HK416':continue # Superseded by HK416NativeRailCorrection: retain the native rail clamps.
        name=f'SM_{entry["kind"]}_{entry["side"]}';folder=D+'/'+entry['family'];path=folder+'/'+name
        if report['saved'].get(key,{}).get('revision')==3 and E.does_asset_exist(path):continue
        existing=u.load_asset(path) if E.does_asset_exist(path) else None
        if existing:
            existing.get_editor_property('asset_import_data').set_editor_property('remove_degenerates',False)
        options=u.FbxImportUI();options.automated_import_should_detect_type=False;options.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
        options.import_mesh=True;options.import_materials=False;options.import_textures=False;options.import_animations=False;options.override_full_name=True
        data=options.static_mesh_import_data;data.combine_meshes=True;data.auto_generate_collision=False;data.generate_lightmap_u_vs=False
        # The reviewed bodies contain tiny optical and surface-detail triangles.
        # The importer's default cleanup removes some of these visible surfaces.
        data.remove_degenerates=False
        data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
        task=u.AssetImportTask();task.filename=entry['fbx'];task.destination_path=folder;task.destination_name=name
        task.automated=True;task.replace_existing=True;task.replace_existing_settings=True;task.save=False;task.options=options;task.factory=u.FbxFactory()
        A.import_asset_tasks([task]);mesh=u.load_asset(path)
        if not task.imported_object_paths or mesh is None:raise RuntimeError('No imported mesh '+path)
        slots=list(mesh.static_materials);bindings={clean(n):p for n,p in entry['materials'].items() if p}
        source=sources[entry['family']]['devices'][entry['kind']]
        bindings.update({clean(m['slot']):m['path'] for m in source['materials']})
        for i,slot in enumerate(slots):
            label=clean(str(slot.material_slot_name));material_path=bindings.get(label)
            if label=='Tactical_Fitted_Bearing':
                material_path='/Game/Weapons/TacticalDevices20260913/BlessedLaser20261006/Materials/M_Blessed_Graphite' if entry['kind']=='blessed_laser' else '/Game/Weapons/ASH12/UniversalAttachments20260919/Materials/M_ASH12_GripMetal_Coat'
            if not material_path:raise RuntimeError('Missing source material binding '+key+' '+label)
            mat=u.load_asset(material_path)
            if mat is None:raise RuntimeError('Missing material '+material_path)
            slot.material_interface=mat
            # Retain legacy body slot names for the approved runtime finish overrides.
            original=next((m['slot'] for m in source['materials'] if m['path']==material_path),None)
            if original and label!='Tactical_Fitted_Bearing':slot.material_slot_name=original
            slots[i]=slot
        mesh.set_editor_property('static_materials',slots)
        for label,position in entry['sockets'].items():
            socket=mesh.find_socket(label)
            if socket is None:
                socket=u.StaticMeshSocket(outer=mesh);socket.set_editor_property('socket_name',label);mesh.add_socket(socket)
            socket.set_editor_property('relative_location',u.Vector(*position))
        E.set_metadata_tag(mesh,'SourceDevice',entry['source'])
        E.set_metadata_tag(mesh,'TacticalMount',f'Side {entry["side"]}: closed fitted bearing; positive scale; original body UVs')
        if not u.EditorLoadingAndSavingUtils.save_packages([mesh.get_outermost()],False):raise RuntimeError('Save failed '+path)
        report['saved'][key]={'revision':3,'path':mesh.get_path_name(),'materials':[{ 'slot':str(s.material_slot_name),'path':s.material_interface.get_path_name()} for s in mesh.static_materials], 'sockets':entry['sockets']}
        receipt.write_text(json.dumps(report,indent=2),encoding='utf-8')
        print('FITTED_TACTICAL_SAVED '+key,flush=True)
finally:u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX '+str(old))
report['status']='generic_assets_saved_HK416_superseded_by_HK416NativeRailCorrection';receipt.write_text(json.dumps(report,indent=2),encoding='utf-8')
