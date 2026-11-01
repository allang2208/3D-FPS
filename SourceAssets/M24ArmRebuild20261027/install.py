"""Save rebuilt full-arm profiles for all M24 roles and both magazine sizes."""
import unreal as u,json,copy,shutil
from pathlib import Path
O=Path(__file__).resolve().parent;D='/Game/Weapons/M24/ArmRebuild20261027'
ACTIVE='/Game/Weapons/M24/MotionPolish20261027'
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools()
src=json.loads((O/'authoring.json').read_text())
R={'complete':False,'saved':[],'runtime_tested':False,'profiles':{},'base_animations_replaced':False}
def record():(O/'install_receipt.json').write_text(json.dumps(R,indent=2),encoding='utf-8')
def load(p):
 a=u.load_asset(p)
 if not a:raise RuntimeError('Missing '+p)
 return a
def save(a):
 if not E.save_loaded_asset(a,False):raise RuntimeError('Save failed '+a.get_path_name())
 R['saved'].append(a.get_path_name());record()
def create(name):
 p=D+'/'+name
 if E.does_asset_exist(p):return load(p)
 f=u.DataAssetFactory();f.set_editor_property('data_asset_class',u.WeaponGripProfile)
 return A.create_asset(name,D,u.WeaponGripProfile,f)
def packed(profile,family):
 return {'family':family,'clips':[{'base':c.get_editor_property('base').get_path_name(),'duration':c.get_editor_property('duration'),'tracks':[
  {'bone':str(t.get_editor_property('bone')),'times':list(t.get_editor_property('times')),'values':list(t.get_editor_property('values'))} for t in c.get_editor_property('tracks')]} for c in profile.get_editor_property('clips')]}
if any(p.get_name().startswith((D,ACTIVE)) for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):
 raise RuntimeError('Unsaved owned M24 polish assets retained')
previous=packed(load('/Game/Weapons/M24/MotionPolish20261027/DA_M24_SupportGrip'),'base')
spec=copy.deepcopy(previous);profile=create('DA_M24_SupportGrip');magazine_rows={}
if not profile.set_shared_clips_from_json(json.dumps(spec)):raise RuntimeError('Cannot initialize retained clips')
skeleton=load('/Game/Weapons/M24/MotionMagazine20261027/SK_M24_MotionV9').skeleton
compression=load('/Game/Weapons/M4InfimaRigV4/BC_M4Viewmodel')
flag='Interchange.FeatureFlags.Import.FBX';old=u.SystemLibrary.get_console_variable_int_value(flag)
u.SystemLibrary.execute_console_command(None,flag+' 0')
try:
 for role,row in src['clips'].items():
  base_role=role.removesuffix('_mag10');folder='Hold20261027' if base_role in ('idle','aim') else 'MotionMagazine20261027'
  base=load('/Game/Weapons/M24/'+folder+'/Animations/A_M24_'+base_role)
  opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_ANIMATION
  opt.import_mesh=False;opt.import_animations=True;opt.import_materials=False;opt.import_textures=False;opt.skeleton=skeleton
  opt.anim_sequence_import_data.set_editor_property('use_default_sample_rate',False)
  opt.anim_sequence_import_data.set_editor_property('custom_sample_rate',30)
  task=u.AssetImportTask();task.filename=row['file'];task.destination_path=D+'/Authoring';task.destination_name='A_M24_'+role
  task.automated=True;task.replace_existing=True;task.replace_existing_settings=True;task.save=False;task.factory=u.FbxFactory();task.options=opt
  A.import_asset_tasks([task]);authored=load(task.destination_path+'/'+task.destination_name)
  authored.set_editor_property('bone_compression_settings',compression)
  if not profile.bake_clip(base,authored):raise RuntimeError('Cannot bake '+role)
  baked=next(c for c in packed(profile,'base')['clips'] if c['base']==base.get_path_name())
  baked['tracks']=[t for t in baked['tracks'] if t['bone'] in row['owned_bones']]
  for t in baked['tracks']:
   for i in range(0,len(t['values']),10):
    t['values'][i+7:i+10]=[0,0,0]
    # The old quick-melee base translates right finger joints. Retain the
    # authored delta that restores their native offsets, rather than preserving
    # that base error by discarding every finger translation correction.
    t['values'][i:i+3]=[0 if abs(v)<.000001 else v for v in t['values'][i:i+3]]
  if role.endswith('_mag10'):magazine_rows[baked['base']]=baked
  else:
   index=next(i for i,c in enumerate(spec['clips']) if c['base']==baked['base']);spec['clips'][index]=baked
 if not profile.set_shared_clips_from_json(json.dumps(spec)):raise RuntimeError('Cannot install base profile')
 save(profile);(O/'support_profile.json').write_text(json.dumps(spec),encoding='utf-8')
 extended=copy.deepcopy(spec);extended['family']='mag10'
 for i,c in enumerate(extended['clips']):
  if c['base'] in magazine_rows:extended['clips'][i]=copy.deepcopy(magazine_rows[c['base']])
 mag=create('DA_M24_Mag10')
 if not mag.set_shared_clips_from_json(json.dumps(extended)):raise RuntimeError('Cannot install magazine profile')
 save(mag);(O/'mag10_profile.json').write_text(json.dumps(extended),encoding='utf-8')
 # Publish into the existing M24 entry points as an asset-only replacement.
 # Keep the prior package bytes once, before touching those exact two assets.
 backup=O/'Backups';backup.mkdir(exist_ok=True)
 for name,data in [('DA_M24_SupportGrip',spec),('DA_M24_Mag10',extended)]:
  current=load(ACTIVE+'/'+name)
  package=Path(u.Paths.project_content_dir())/'Weapons/M24/MotionPolish20261027'/(name+'.uasset')
  destination=backup/(name+'.uasset')
  if not destination.exists():shutil.copy2(package,destination)
  if not current.set_shared_clips_from_json(json.dumps(data)):raise RuntimeError('Cannot publish active '+name)
  save(current)
 R['active_profile_directory']=ACTIVE
 R['native_interface_changes_required']=False
 for name,data in [('base',spec),('mag10',extended)]:
  R['profiles'][name]=[{'base':c['base'],'duration':c['duration'],'bones':[t['bone'] for t in c['tracks']]} for c in data['clips']]
 record()
 R['complete']=True;record()
finally:u.SystemLibrary.execute_console_command(None,flag+' '+str(old))
print('M24_ARM_REBUILD_SAVED',len(R['saved']),flush=True)
