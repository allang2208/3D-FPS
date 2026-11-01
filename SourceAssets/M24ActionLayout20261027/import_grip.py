import unreal as u,json
from pathlib import Path
O=Path(__file__).resolve().parent;ROOT='/Game/Weapons/M24/ActionLayout20261027/Animations'
src=json.loads((O/'grip_authoring.json').read_text());mesh=u.load_asset('/Game/Weapons/M24/Hold20261027/SK_M24_HoldV9')
compression=u.load_asset('/Game/Weapons/M4InfimaRigV4/BC_M4Viewmodel');receipt={'complete':False,'saved':[]}
old=u.SystemLibrary.get_console_variable_int_value('Interchange.FeatureFlags.Import.FBX')
u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
try:
    for role,row in src['clips'].items():
        opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_ANIMATION
        opt.import_mesh=False;opt.import_animations=True;opt.skeleton=mesh.skeleton
        opt.anim_sequence_import_data.set_editor_property('use_default_sample_rate',False)
        opt.anim_sequence_import_data.set_editor_property('custom_sample_rate',30)
        t=u.AssetImportTask();t.filename=row['file'];t.destination_path=ROOT;t.destination_name='A_M24_'+role
        t.automated=True;t.replace_existing=True;t.replace_existing_settings=True;t.options=opt;t.save=False
        u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([t]);clip=u.load_asset(ROOT+'/A_M24_'+role)
        if not clip:raise RuntimeError('Animation import failed: '+role)
        clip.set_editor_property('bone_compression_settings',compression)
        if not u.EditorAssetLibrary.save_loaded_asset(clip,False):raise RuntimeError('Animation save failed: '+role)
        receipt['saved'].append({'asset':clip.get_path_name(),'duration':clip.get_play_length()})
    receipt['complete']=True
finally:
    u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX '+str(old))
    (O/'grip_import_receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print('M24_BOLT_GRIP_SAVED',len(receipt['saved']),flush=True)
