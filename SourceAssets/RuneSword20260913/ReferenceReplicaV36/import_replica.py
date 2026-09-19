"""Import only the new rune-sword F-key inspection and its editable reference."""
import json
import shutil
from pathlib import Path
import unreal as u

P=Path(__file__).parent
ROOT=P.parents[2]
DEST='/Game/Weapons/AzureRunesword20260913'
NAME='A_RuneSword_Inspect'
flag='Interchange.FeatureFlags.Import.FBX'
previous=u.SystemLibrary.get_console_variable_int_value(flag)
current=ROOT/'Content/Weapons/AzureRunesword20260913'/(NAME+'.uasset')
backup=P/'Before'/(NAME+'.uasset')
if current.exists() and not backup.exists():
    backup.parent.mkdir(exist_ok=True)
    shutil.copy2(current,backup)
try:
    u.SystemLibrary.execute_console_command(None,flag+' 0')
    mesh=u.load_asset(DEST+'/SK_AzureRunesword_Manny')
    compression=u.load_asset('/Game/Weapons/M4InfimaRigV4/BC_M4Viewmodel')
    records=[]
    for name,destination in [('A_RuneSword_Reference_76_78',DEST+'/ReferenceReplicaV36'),(NAME,DEST)]:
        ui=u.FbxImportUI()
        ui.automated_import_should_detect_type=False
        ui.mesh_type_to_import=u.FBXImportType.FBXIT_ANIMATION
        ui.import_mesh=False;ui.import_animations=True
        ui.import_materials=False;ui.import_textures=False
        ui.skeleton=mesh.skeleton
        ui.anim_sequence_import_data.set_editor_property('use_default_sample_rate',False)
        ui.anim_sequence_import_data.set_editor_property('custom_sample_rate',120)
        task=u.AssetImportTask()
        task.filename=str(P/'Export'/(name+'.fbx'))
        task.destination_path=destination;task.destination_name=name
        task.automated=True;task.replace_existing=True;task.save=False;task.options=ui
        u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
        sequence=u.load_asset(destination+'/'+name)
        if not task.imported_object_paths or not sequence:
            raise RuntimeError('Animation import failed: '+name)
        if compression:sequence.set_editor_property('bone_compression_settings',compression)
        if not u.EditorAssetLibrary.save_loaded_asset(sequence):
            raise RuntimeError('Animation save failed: '+name)
        records.append({'asset':sequence.get_path_name(),'source':task.filename,
                        'duration':sequence.get_play_length(),'saved':True})
    (P/'import_receipt.json').write_text(json.dumps({
        'revision':'ReferenceReplicaV36','imports':records,
        'runtime_entry':'Existing URuneSwordComponent::BeginInspect -> A_RuneSword_Inspect',
        'source_video_seconds':[76,78],'reference_interval_in_inspect':[.35,2.35],
        'scope':'Rune sword Inspect only; accepted Equip/Guard/Charge and other swords unchanged',
        'testing':'No PIE, playback, render or animation acceptance performed'
    },indent=2),encoding='utf-8')
    u.log('REFERENCE_REPLICA_IMPORT_COMPLETE')
finally:
    u.SystemLibrary.execute_console_command(None,f'{flag} {previous}')
