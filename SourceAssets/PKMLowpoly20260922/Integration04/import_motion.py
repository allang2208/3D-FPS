import unreal as u,json
from pathlib import Path
O=Path(__file__).parent;P='/Game/Weapons/PKMLowpoly20260922';A=u.AssetToolsHelpers.get_asset_tools();mesh=u.load_asset(P+'/SK_PKM_Manny')
if not mesh:raise RuntimeError('PKM geometry is required')
report={};source=json.loads((O/'authoring.json').read_text(encoding='utf-8'))
for key,duration in source['clips'].items():
 name='A_PKM_'+key;opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_ANIMATION;opt.skeleton=mesh.skeleton;opt.import_mesh=False;opt.import_animations=True;opt.import_materials=False;opt.import_textures=False
 opt.anim_sequence_import_data.set_editor_property('use_default_sample_rate',False);opt.anim_sequence_import_data.set_editor_property('custom_sample_rate',60)
 task=u.AssetImportTask();task.filename=str(O/'Exports'/(name+'.fbx'));task.destination_path=P+'/Animations';task.destination_name=name;task.options=opt;task.factory=u.FbxFactory();task.automated=True;task.replace_existing=True;task.save=True
 flag='Interchange.FeatureFlags.Import.FBX';prior=u.SystemLibrary.get_console_variable_int_value(flag)
 try:
  u.SystemLibrary.execute_console_command(None,flag+' 0');A.import_asset_tasks([task])
 finally:u.SystemLibrary.execute_console_command(None,flag+' '+str(prior))
 clip=u.load_asset(task.destination_path+'/'+name)
 if not clip:raise RuntimeError('Animation import failed: '+name)
 clip.set_editor_property('bone_compression_settings',u.load_asset('/Game/Weapons/M4InfimaRigV4/BC_M4Viewmodel'))
 if not u.EditorAssetLibrary.save_loaded_asset(clip,False):raise RuntimeError('Animation save failed: '+name)
 report[key]={'asset':clip.get_path_name(),'seconds':clip.get_play_length()};(O/'motion_import.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
u.log('PKM animation set saved. No PIE or runtime test performed.')
