"""Replace only repaired motion assets; preserve every mesh/equipment bind."""
import unreal as u,json,hashlib
from pathlib import Path
O=Path(__file__).parent;P=O.parents[1];S=P/'SourceAssets/BenelliM4Super9020261006'
ROOT='/Game/Weapons/Super90/Cransh20261006'
auth=json.loads((O/'authoring_receipt.json').read_text())
mesh=u.load_asset(ROOT+'/SK_Super90_V7');E=u.EditorAssetLibrary
if not mesh:raise RuntimeError('Missing Super90 native mesh')
receipt={'animations_saved':[],'mesh_bind_changed':False,'runtime_tested':False}
flag='Interchange.FeatureFlags.Import.FBX';previous=u.SystemLibrary.get_console_variable_int_value(flag)
u.SystemLibrary.execute_console_command(None,flag+' 0')
try:
    for kind,row in auth['clips'].items():
        file=Path(row['fbx']);name='A_Super90_'+kind
        options=u.FbxImportUI();options.automated_import_should_detect_type=False
        options.mesh_type_to_import=u.FBXImportType.FBXIT_ANIMATION;options.import_mesh=False;options.import_animations=True;options.skeleton=mesh.skeleton
        options.anim_sequence_import_data.set_editor_property('use_default_sample_rate',False)
        options.anim_sequence_import_data.set_editor_property('custom_sample_rate',60)
        task=u.AssetImportTask();task.filename=str(file);task.destination_path=ROOT+'/Animations';task.destination_name=name
        task.automated=True;task.replace_existing=True;task.replace_existing_settings=True;task.save=False;task.options=options;task.factory=u.FbxFactory()
        u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
        asset=u.load_asset(ROOT+'/Animations/'+name)
        if not asset:raise RuntimeError('Import failed '+name)
        asset.set_editor_property('bone_compression_settings',u.load_asset('/Game/Weapons/M4InfimaRigV4/BC_M4Viewmodel'))
        E.set_metadata_tag(asset,'Super90SourceSHA256',hashlib.sha256(file.read_bytes()).hexdigest())
        E.set_metadata_tag(asset,'Super90PoseBasisRepair','20261007: source deformation transported to actual native bind')
        if not u.EditorLoadingAndSavingUtils.save_packages([asset.get_outermost()],False):raise RuntimeError('Save failed '+name)
        receipt['animations_saved'].append(asset.get_path_name())
        (O/'import_receipt.json').write_text(json.dumps(receipt,indent=2))
finally:u.SystemLibrary.execute_console_command(None,flag+' '+str(previous))
print('SUPER90_REPAIRED_ANIMATIONS_SAVED',len(receipt['animations_saved']))
