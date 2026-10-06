"""Replace and save the fifteen repaired mounts through the existing UE bridge.

Existing approved materials, tuning, beam effects and weather tables are kept.
"""
import json,re
from pathlib import Path
import unreal as u
P=Path(__file__).resolve().parents[3];O=P/'SourceAssets/BlessedLaser20261006/Model';R=O/'MountRepair'
D='/Game/Weapons/TacticalDevices20260913/BlessedLaser20261006';A=u.AssetToolsHelpers.get_asset_tools();E=u.EditorAssetLibrary
auth=json.loads((O/'authoring.json').read_text());prior=json.loads((R/'Inputs/authoring-v1.json').read_text())
targets={D+'/Models/SM_BlessedLaser_'+family for family in auth}
if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():
    raise RuntimeError('Mount import deferred: an active play world owns the weapon models. Stop Play in this editor first.')
dirty={p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
conflict=targets.intersection(dirty)
if conflict:raise RuntimeError('Mount assets contain unsaved editor edits: '+', '.join(sorted(conflict)))
materials={key:u.load_asset(D+'/Materials/M_'+key) for key in ('Blessed_Graphite','Blessed_Gold','Blessed_Black','Blessed_Optic','Blessed_Aperture')}
report={'revision':2,'saved':[],'models':{},'game_tested':False};receipt=R/'import-mounts-v2-receipt.json'
def clean(s):return re.sub(r'[._]\d{3}$','',str(s))
old=u.SystemLibrary.get_console_variable_int_value('Interchange.FeatureFlags.Import.FBX')
u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
try:
    for family,entry in auth.items():
        if entry.get('mount_revision')!=2:raise RuntimeError('Expected repaired mount recipe: '+family)
        name='SM_BlessedLaser_'+family;path=D+'/Models/'+name
        options=u.FbxImportUI();options.automated_import_should_detect_type=False;options.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
        options.import_mesh=True;options.import_materials=False;options.import_textures=False;options.import_animations=False;options.override_full_name=True
        data=options.static_mesh_import_data;data.combine_meshes=True;data.auto_generate_collision=False;data.generate_lightmap_u_vs=False
        data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS;data.vertex_color_import_option=u.VertexColorImportOption.REPLACE
        task=u.AssetImportTask();task.filename=entry['fbx'];task.destination_path=D+'/Models';task.destination_name=name
        task.automated=True;task.replace_existing=True;task.replace_existing_settings=True;task.save=False;task.options=options;task.factory=u.FbxFactory()
        A.import_asset_tasks([task]);mesh=u.load_asset(path)
        if not task.imported_object_paths or mesh is None:raise RuntimeError('FBX import did not produce '+family)
        bindings={};slots=list(mesh.static_materials);retained={**prior[family]['retained_materials'],**entry['retained_materials']}
        for i,slot in enumerate(slots):
            key=clean(slot.material_slot_name);mat=materials.get(key)
            if mat is None:
                source=next((value for label,value in retained.items() if clean(label)==key),None)
                if source:mat=u.load_asset(source)
            if mat is None:raise RuntimeError('Missing source material binding '+family+'/'+key)
            slot.material_interface=mat;slots[i]=slot;bindings[str(slot.material_slot_name)]=mat.get_path_name()
        mesh.set_editor_property('static_materials',slots)
        for socket_name,position in entry['sockets_ue_cm'].items():
            socket=mesh.find_socket(socket_name)
            if socket is None:
                socket=u.StaticMeshSocket(outer=mesh);socket.set_editor_property('socket_name',socket_name);mesh.add_socket(socket)
            socket.set_editor_property('relative_location',u.Vector(*position))
        E.set_metadata_tag(mesh,'BlessedEmitterModel','concept-01-hard-surface-mount-v2')
        E.set_metadata_tag(mesh,'MountSource',str(R/'Editable'/('BlessedLaser_'+family+'_MountV2.blend')))
        E.set_metadata_tag(mesh,'MountRevision','2')
        if not u.EditorLoadingAndSavingUtils.save_packages([mesh.get_outermost()],False):raise RuntimeError('Package save failed: '+family)
        report['saved'].append(mesh.get_path_name());report['models'][family]={'asset':mesh.get_path_name(),'fbx':entry['fbx'],'materials':bindings,'sockets_ue_cm':entry['sockets_ue_cm'],'contact_geometry':entry['contact_geometry']}
        receipt.write_text(json.dumps(report,indent=2),encoding='utf-8');print('BLESSED_MOUNT_SAVED '+family)
finally:u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX '+str(old))
report['status']='fifteen_mount_assets_imported_and_saved';receipt.write_text(json.dumps(report,indent=2),encoding='utf-8')
print('BLESSED_MOUNT_V2_COMPLETE '+str(len(report['saved'])))
