"""Import G18 drum author clips and save the shared reload pose profile."""
import unreal as u,json,runpy
from pathlib import Path
O=Path(__file__).parent;S=O.parents[1]
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools()
ROOT='/Game/Weapons/G18/Drum50_20261003/Reload'
spec=json.loads((O/'manifest.json').read_text())['profiles'][0]
mesh=u.load_asset(spec['mesh']);skeleton=mesh.skeleton
report={'complete':False,'saved':[],'runtime_tested':False}
flag='Interchange.FeatureFlags.Import.FBX';old=u.SystemLibrary.get_console_variable_int_value(flag)
u.SystemLibrary.execute_console_command(None,flag+' 0')
try:
    for kind in ('reload','reload_empty'):
        name='A_G18_Drum50_'+kind
        opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_ANIMATION
        opt.import_mesh=False;opt.import_animations=True;opt.skeleton=skeleton
        opt.anim_sequence_import_data.set_editor_property('use_default_sample_rate',False)
        opt.anim_sequence_import_data.set_editor_property('custom_sample_rate',120)
        task=u.AssetImportTask();task.filename=str(O/(name+'.fbx'));task.destination_path=ROOT+'/Authored';task.destination_name=name
        task.automated=True;task.replace_existing=True;task.replace_existing_settings=True;task.save=False;task.options=opt;task.factory=u.FbxFactory()
        A.import_asset_tasks([task]);clip=u.load_asset(ROOT+'/Authored/'+name)
        if not clip:raise RuntimeError('Animation import failed '+name)
        clip.set_editor_property('bone_compression_settings',u.load_asset('/Game/Weapons/M4InfimaRigV4/BC_M4Viewmodel'))
        if not E.save_loaded_asset(clip,False):raise RuntimeError('Animation save failed '+name)
        report['saved'].append(clip.get_path_name())
        (O/'import_receipt.json').write_text(json.dumps(report,indent=2))
finally:u.SystemLibrary.execute_console_command(None,flag+' '+str(old))
production=runpy.run_path(str(S/'WeaponAnimationSharing20261001/install_profiles.py'),init_globals={
    'ANIMATION_SHARING_JOB_ROOT':str(O),'ANIMATION_SHARING_AUTHOR':'G18Drum50Reload20261003'})
if not production['receipt']['complete']:raise RuntimeError('G18 drum reload profile production is incomplete')
report['complete']=True;report['profile']=spec['asset']
(O/'import_receipt.json').write_text(json.dumps(report,indent=2))
print('G18_DRUM50_RELOAD_AND_SHARED_PROFILE_SAVED',flush=True)
