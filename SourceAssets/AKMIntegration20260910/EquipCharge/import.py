import unreal as u,json
from pathlib import Path
O=Path(__file__).parent;P='/Game/Weapons/AKMIntegration/EquipCharge'
m=u.load_asset('/Game/Weapons/AKMIntegration/WalnutFab/SK_AKM_MannyNative');assert m
opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_ANIMATION;opt.skeleton=m.skeleton;opt.import_mesh=False;opt.import_animations=True;opt.import_materials=False;opt.import_textures=False;opt.anim_sequence_import_data.set_editor_property('use_default_sample_rate',False);opt.anim_sequence_import_data.set_editor_property('custom_sample_rate',120)
t=u.AssetImportTask();t.filename=str(O/'A_AKM_equip.fbx');t.destination_path=P;t.destination_name='A_AKM_equip';t.automated=True;t.replace_existing=True;t.save=True;t.options=opt
u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([t]);a=u.load_asset(P+'/A_AKM_equip');assert a and abs(a.get_play_length()-1.7)<.001
a.set_editor_property('bone_compression_settings',u.load_asset('/Game/Weapons/M4InfimaRigV4/BC_M4Viewmodel'));assert u.EditorAssetLibrary.save_loaded_asset(a,False)
(O/'import.json').write_text(json.dumps({'asset':a.get_path_name(),'duration':a.get_play_length()},indent=2));u.log('AKM_EQUIP_CHARGE_IMPORT_PASS')
