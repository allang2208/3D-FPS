"""Install only the new equip clip at its existing runtime path."""
import json,shutil
from pathlib import Path
import unreal as u
P=Path(__file__).parent;D='/Game/Weapons/AzureRunesword20260913';NAME='A_RuneSword_Equip'
flag='Interchange.FeatureFlags.Import.FBX'
previous=u.SystemLibrary.get_console_variable_int_value(flag)
try:
    u.SystemLibrary.execute_console_command(None,flag+' 0')
    current=P.parents[2]/'Content/Weapons/AzureRunesword20260913'/(NAME+'.uasset')
    backup=P/'Before'/(NAME+'.uasset')
    if current.exists() and not backup.exists():
        backup.parent.mkdir(exist_ok=True);shutil.copy2(current,backup)
    options=u.FbxImportUI();options.automated_import_should_detect_type=False
    options.mesh_type_to_import=u.FBXImportType.FBXIT_ANIMATION
    options.import_mesh=False;options.import_animations=True
    options.import_materials=False;options.import_textures=False
    options.skeleton=u.load_asset(D+'/SK_AzureRunesword_Manny').skeleton
    options.anim_sequence_import_data.set_editor_property('use_default_sample_rate',False)
    options.anim_sequence_import_data.set_editor_property('custom_sample_rate',480)
    task=u.AssetImportTask();task.filename=str(P/'Export'/(NAME+'.fbx'))
    task.destination_path=D;task.destination_name=NAME;task.automated=True
    task.replace_existing=True;task.save=False;task.options=options
    u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    sequence=u.load_asset(D+'/'+NAME)
    if not task.imported_object_paths or not sequence:raise RuntimeError('Equip import failed')
    compression=u.load_asset('/Game/Weapons/M4InfimaRigV4/BC_M4Viewmodel')
    if compression:sequence.set_editor_property('bone_compression_settings',compression)
    if not u.EditorAssetLibrary.save_loaded_asset(sequence):raise RuntimeError('Equip save failed')
    (P/'import_receipt.json').write_text(json.dumps({'source':task.filename,'asset':sequence.get_path_name(),
        'duration':sequence.get_play_length(),'scope':'Equip only; other runtime actions retained'},indent=2),encoding='utf-8')
    u.log('RUNESWORD_V23_EQUIP_IMPORT_COMPLETE')
finally:
    u.SystemLibrary.execute_console_command(None,f'{flag} {previous}')
