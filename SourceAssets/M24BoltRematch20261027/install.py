"""Save only the M24 right-arm bolt stroke into the two existing profiles."""
import unreal as u,json,copy,shutil,hashlib
from pathlib import Path
O=Path(__file__).resolve().parent;D='/Game/Weapons/M24/BoltRematch20261027';ACTIVE='/Game/Weapons/M24/MotionPolish20261027'
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();src=json.loads((O/'authoring.json').read_text())
R={'complete':False,'saved':[],'runtime_tested':False,'base_animations_replaced':False,'clips':{},'scope':'right arm fire, cycle, empty reload including mag10'}
def record():(O/'install_receipt.json').write_text(json.dumps(R,indent=2))
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
def packed(p,family):
 return {'family':family,'clips':[{'base':c.get_editor_property('base').get_path_name(),'duration':c.get_editor_property('duration'),'tracks':[
 {'bone':str(t.get_editor_property('bone')),'times':list(t.get_editor_property('times')),'values':list(t.get_editor_property('values'))} for t in c.get_editor_property('tracks')]} for c in p.get_editor_property('clips')]}
if any(p.get_name().startswith((D,ACTIVE)) for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):raise RuntimeError('Unsaved M24 profiles retained; publication did not run')
names={'base':'DA_M24_SupportGrip','mag10':'DA_M24_Mag10'}
live={family:load(ACTIVE+'/'+name) for family,name in names.items()}
before={family:packed(p,family) for family,p in live.items()}
backup=O/'Backups';backup.mkdir(exist_ok=True)
for family,name in names.items():
 path=Path(u.Paths.project_content_dir())/'Weapons/M24/MotionPolish20261027'/(name+'.uasset')
 dest=backup/(name+'.uasset')
 if not dest.exists():shutil.copy2(path,dest)
 (backup/(name+'.json')).write_text(json.dumps(before[family]))
spec=copy.deepcopy(before);scratch=create('DA_M24_Authoring')
if not scratch.set_shared_clips_from_json(json.dumps(before['base'])):raise RuntimeError('Cannot initialize baking profile')
skeleton=load('/Game/Weapons/M24/MotionMagazine20261027/SK_M24_MotionV9').skeleton
compression=load('/Game/Weapons/M4InfimaRigV4/BC_M4Viewmodel')
flag='Interchange.FeatureFlags.Import.FBX';old=u.SystemLibrary.get_console_variable_int_value(flag);u.SystemLibrary.execute_console_command(None,flag+' 0')
try:
 for role,row in src['clips'].items():
  base_role=role.removesuffix('_mag10');base=load('/Game/Weapons/M24/MotionMagazine20261027/Animations/A_M24_'+base_role)
  opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_ANIMATION
  opt.import_mesh=False;opt.import_animations=True;opt.import_materials=False;opt.import_textures=False;opt.skeleton=skeleton
  opt.anim_sequence_import_data.set_editor_property('use_default_sample_rate',False);opt.anim_sequence_import_data.set_editor_property('custom_sample_rate',30)
  task=u.AssetImportTask();task.filename=row['file'];task.destination_path=D+'/Authoring';task.destination_name='A_M24_'+role
  task.automated=True;task.replace_existing=True;task.replace_existing_settings=True;task.save=False;task.factory=u.FbxFactory();task.options=opt
  A.import_asset_tasks([task]);authored=load(task.destination_path+'/'+task.destination_name);authored.set_editor_property('bone_compression_settings',compression)
  if not scratch.bake_clip(base,authored):raise RuntimeError('Cannot bake '+role)
  baked=next(c for c in packed(scratch,'base')['clips'] if c['base']==base.get_path_name())
  owned=set(row['owned_bones']);tracks=[t for t in baked['tracks'] if t['bone'] in owned]
  for t in tracks:
   for i in range(0,len(t['values']),10):
    t['values'][i+7:i+10]=[0,0,0]
    t['values'][i:i+3]=[0 if abs(v)<.000001 else v for v in t['values'][i:i+3]]
  families=['mag10'] if role.endswith('_mag10') else ['base','mag10']
  for family in families:
   target=next(c for c in spec[family]['clips'] if c['base']==baked['base'])
   target['tracks']=[t for t in target['tracks'] if t['bone'] not in owned]+copy.deepcopy(tracks)
  R['clips'][role]={'base':baked['base'],'replaced_bones':sorted(owned),'retained_duration':baked['duration']}
 for family,name in names.items():
  p=create(name)
  if not p.set_shared_clips_from_json(json.dumps(spec[family])):raise RuntimeError('Cannot save candidate '+name)
  save(p)
 for family,name in names.items():
  if not live[family].set_shared_clips_from_json(json.dumps(spec[family])):raise RuntimeError('Cannot publish '+name)
  save(live[family]);(O/(family+'_profile.json')).write_text(json.dumps(spec[family]))
 R['complete']=True;R['active_profile_directory']=ACTIVE;R['native_build_required']=False;record()
finally:u.SystemLibrary.execute_console_command(None,flag+' '+str(old))
print('M24_BOLT_REMATCH_SAVED',len(R['saved']),flush=True)
