"""Import/save authored support animations; retain the installed native mesh."""
import json,unreal as u
from pathlib import Path
O=Path('D:/FPS3D/FPSGAME/SourceAssets/LMG20120260927/ArmSprint06');R='/Game/Weapons/LMG201/Production20260927';B='/Game/Weapons/LMG201/ArmSprint06/Before'
if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():raise RuntimeError('PIE active; 201 support animations not changed')
auth=json.loads((O/'motion_authoring.json').read_text());A=u.AssetToolsHelpers.get_asset_tools();E=u.EditorAssetLibrary
receipt=json.loads((O/'import_receipt.json').read_text()) if (O/'import_receipt.json').exists() else {'animations':{},'backups':{},'mesh_modified':False,'runtime_tested':False,'visual_tested':False,'source_checks_completed':True,'status':'importing'}
mesh=u.load_asset(R+'/SK_LMG201_Manny')
def record():(O/'import_receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
def save(a):
 if not a or not E.save_loaded_asset(a,False):raise RuntimeError('Asset save failed '+str(a))
flag='Interchange.FeatureFlags.Import.FBX';prior=u.SystemLibrary.get_console_variable_int_value(flag);u.SystemLibrary.execute_console_command(None,flag+' 0')
try:
 for key,d in auth['animations'].items():
  if key in receipt['animations']:continue
  name='A_LMG201_'+key;path=R+'/Animations/'+name;dest=B+'/Animations/'+name
  previous=u.load_asset(dest) or E.duplicate_asset(path,dest);save(previous);receipt['backups'][path]=previous.get_path_name();record()
  opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_ANIMATION;opt.skeleton=mesh.skeleton;opt.import_mesh=False;opt.import_animations=True;opt.import_materials=False;opt.import_textures=False
  opt.anim_sequence_import_data.set_editor_property('use_default_sample_rate',False);opt.anim_sequence_import_data.set_editor_property('custom_sample_rate',round(d['fps']))
  task=u.AssetImportTask();task.filename=str(O/'Exports'/(name+'.fbx'));task.destination_path=R+'/Animations';task.destination_name=name;task.options=opt;task.factory=u.FbxFactory();task.automated=True;task.replace_existing=True;task.replace_existing_settings=True;task.save=False;A.import_asset_tasks([task])
  clip=u.load_asset(path)
  if not clip or not task.imported_object_paths:raise RuntimeError('Animation import failed '+name)
  clip.set_editor_property('bone_compression_settings',u.load_asset('/Game/Weapons/M4InfimaRigV4/BC_M4Viewmodel'));save(clip)
  receipt['animations'][key]={'asset':clip.get_path_name(),'seconds':clip.get_play_length(),'modified_tracks':d['modified_tracks']};record()
finally:u.SystemLibrary.execute_console_command(None,flag+' '+str(prior))
receipt['status']='imported_and_saved';receipt['shared_skeleton']=mesh.skeleton.get_path_name();record();print('LMG201_ARMSPRINT06_ANIMATIONS_SAVED',len(receipt['animations']))
