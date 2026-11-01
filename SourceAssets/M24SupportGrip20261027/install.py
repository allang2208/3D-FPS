"""Bake only finger corrections, compose the existing magazine layer, save two DAs."""
import unreal as u,json,copy
from pathlib import Path
O=Path(__file__).resolve().parent;D='/Game/Weapons/M24/SupportGrip20261027'
src=json.loads((O/'authoring.json').read_text());E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools()
R={'complete':False,'saved':[],'runtime_tested':False,'profiles':{},'original_animations_replaced':False,'mesh_replaced':False}
def record():(O/'install_receipt.json').write_text(json.dumps(R,indent=2),encoding='utf-8')
def load(p):
 ob=u.load_asset(p)
 if not ob:raise RuntimeError('Missing asset '+p)
 return ob
def save(ob):
 if not E.save_loaded_asset(ob,False):raise RuntimeError('Could not save '+ob.get_path_name())
 R['saved'].append(ob.get_path_name());record()
def create(name):
 path=D+'/'+name
 if E.does_asset_exist(path):return load(path)
 factory=u.DataAssetFactory();factory.set_editor_property('data_asset_class',u.WeaponGripProfile)
 return A.create_asset(name,D,u.WeaponGripProfile,factory)
def packed(profile,family,allowed=None):
 result={'family':family,'clips':[]}
 for c in profile.get_editor_property('clips'):
  row={'base':c.get_editor_property('base').get_path_name(),'duration':c.get_editor_property('duration'),'tracks':[]}
  for t in c.get_editor_property('tracks'):
   name=str(t.get_editor_property('bone'))
   if allowed is not None and name not in allowed:continue
   values=list(t.get_editor_property('values'))
   if allowed is not None:
    # This layer changes rotations only. Remove floating-point translation
    # and scale noise introduced by FBX; native finger lengths stay exact.
    for i in range(0,len(values),10):values[i:i+3]=[0,0,0];values[i+7:i+10]=[0,0,0]
   row['tracks'].append({'bone':name,'times':list(t.get_editor_property('times')),'values':values})
  result['clips'].append(row)
 return result
dirty={p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if any(p.startswith(D) for p in dirty):raise RuntimeError('Unsaved support-grip assets; retained without overwrite')
mesh=load('/Game/Weapons/M24/MotionMagazine20261027/SK_M24_MotionV9');skeleton=mesh.skeleton
previous_mag=packed(load('/Game/Weapons/M24/MotionMagazine20261027/DA_M24_Mag10'),'mag10')
compression=load('/Game/Weapons/M4InfimaRigV4/BC_M4Viewmodel')
profile=create('DA_M24_SupportGrip');flag='Interchange.FeatureFlags.Import.FBX';old=u.SystemLibrary.get_console_variable_int_value(flag)
u.SystemLibrary.execute_console_command(None,flag+' 0')
try:
 for role,row in src['clips'].items():
  if role.endswith('_mag10'):continue
  folder='Hold20261027' if role in ('idle','aim') else 'MotionMagazine20261027'
  base=load('/Game/Weapons/M24/'+folder+'/Animations/A_M24_'+role)
  opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_ANIMATION
  opt.import_mesh=False;opt.import_animations=True;opt.import_materials=False;opt.import_textures=False;opt.skeleton=skeleton
  opt.anim_sequence_import_data.set_editor_property('use_default_sample_rate',False);opt.anim_sequence_import_data.set_editor_property('custom_sample_rate',30)
  task=u.AssetImportTask();task.filename=row['file'];task.destination_path=D+'/Authoring';task.destination_name='A_M24_'+role
  task.automated=True;task.replace_existing=True;task.replace_existing_settings=True;task.save=False;task.factory=u.FbxFactory();task.options=opt
  A.import_asset_tasks([task]);authored=load(task.destination_path+'/'+task.destination_name);authored.set_editor_property('bone_compression_settings',compression)
  if not profile.bake_clip(base,authored):raise RuntimeError('Cannot bake support layer '+role)
 # Only the native left digits belong to this correction. Preserve all other
 # channels by construction, including the existing right-hand bolt contact.
 spec=packed(profile,'base',set(src['target_local']))
 if not profile.set_shared_clips_from_json(json.dumps(spec)):raise RuntimeError('Cannot install finger layer')
 save(profile);(O/'support_profile.json').write_text(json.dumps(spec),encoding='utf-8')
 # These layers affect disjoint local bones. Compose exact saved magazine-arm
 # deltas with new finger deltas, without re-solving the accepted floorplate path.
 extended=copy.deepcopy(spec);extended['family']='mag10'
 for row in extended['clips']:
  oldrow=next((c for c in previous_mag['clips'] if c['base']==row['base']),None)
  if oldrow:
   own={t['bone'] for t in row['tracks']}
   if own.intersection(t['bone'] for t in oldrow['tracks']):raise RuntimeError('Unexpected overlapping magazine/finger bones')
   row['tracks'].extend(oldrow['tracks'])
 mag=create('DA_M24_Mag10')
 if not mag.set_shared_clips_from_json(json.dumps(extended)):raise RuntimeError('Cannot install extended-magazine support layer')
 save(mag);(O/'mag10_profile.json').write_text(json.dumps(extended),encoding='utf-8')
 for name,data in [('base',spec),('mag10',extended)]:
  R['profiles'][name]=[{'base':c['base'],'duration':c['duration'],'bones':[t['bone'] for t in c['tracks']]} for c in data['clips']]
 R['complete']=True;record()
finally:u.SystemLibrary.execute_console_command(None,flag+' '+str(old))
print('M24_SUPPORT_GRIP_SAVED',len(R['saved']),flush=True)
