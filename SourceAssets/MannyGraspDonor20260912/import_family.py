import unreal as u,json
from pathlib import Path
O=Path(__file__).parent/'Final'
build=json.loads((O/'build.json').read_text());assert len(build)==18
A=u.AssetToolsHelpers.get_asset_tools();report={}
for key,info in build.items():
 weapon,clip=key.split(':');variant='Vertical' if weapon=='m4' else 'vertical';name=f'A_{weapon.upper()}_{variant}_{clip}'
 mesh=u.load_asset('/Game/Weapons/M4HK416Replica/SK_M4_FoldingSights_HK416' if weapon=='m4' else '/Game/Weapons/AKMIntegration/SovietFab/Attachments/SK_AKM_MannyNative')
 dest='/Game/Weapons/M4VerticalGripVRENatural/Vertical' if weapon=='m4' else '/Game/Weapons/AKMIntegration/SovietFab/GripVRENatural/vertical'
 opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_ANIMATION;opt.skeleton=mesh.skeleton;opt.import_mesh=False;opt.import_animations=True;opt.import_materials=False;opt.import_textures=False
 opt.anim_sequence_import_data.set_editor_property('use_default_sample_rate',False);opt.anim_sequence_import_data.set_editor_property('custom_sample_rate',info['sample_rate'])
 task=u.AssetImportTask();task.filename=info['output'];task.destination_path=dest;task.destination_name=name;task.options=opt;task.automated=True;task.replace_existing=True;task.save=False;A.import_asset_tasks([task])
 asset=u.load_asset(dest+'/'+name);assert asset
 asset.set_editor_property('bone_compression_settings',u.load_asset('/Game/Weapons/M4InfimaRigV4/BC_M4Viewmodel'));u.AKMAnimationAuditLibrary.finish_animation_compression(asset)
 assert u.EditorAssetLibrary.save_loaded_asset(asset,False)
 assert asset.get_editor_property('skeleton')==mesh.skeleton and abs(asset.get_play_length()-info['duration'])<.0001
 report[key]={'asset':asset.get_path_name(),'duration':asset.get_play_length(),'source':task.filename}
 (O/'import.json').write_text(json.dumps(report,indent=2));u.log('VRE_GRIP_IMPORTED '+key)
u.log('VRE_GRIP_IMPORT_PASS 18')
