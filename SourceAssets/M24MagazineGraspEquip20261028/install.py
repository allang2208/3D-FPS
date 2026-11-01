"""Publish four magazine-contact layers and the complete M24 equip action."""
import unreal as u,json,copy,shutil,ast,hashlib,bisect,math
from pathlib import Path
O=Path(__file__).resolve().parent;E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools()
tree=ast.parse((O.parent/'M24ReloadRefine20261028/install.py').read_text())
for name in ('packed','find','qlerp','sample'):
 exec(compile(ast.unparse(next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name==name)),name,'exec'))
world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
if world:raise RuntimeError('PIE is active; no M24 assets modified')
patch=json.loads((O/'reload_patch.json').read_text());snapshot=json.loads((O/'ue_before.json').read_text());read=json.loads((O/'read_receipt.json').read_text())
paths={f:'/Game/Weapons/M24/MotionPolish20261027/'+n for f,n in {'base':'DA_M24_SupportGrip','mag10':'DA_M24_Mag10'}.items()}
equip_path=snapshot['clips']['equip']['path'];equip_package=equip_path.split('.')[0]
dirty={p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if any(p in dirty for p in [*paths.values(),equip_package]):raise RuntimeError('Unsaved M24 target retained')
live={f:u.load_asset(p) for f,p in paths.items()};before={f:packed(p,f) for f,p in live.items()};spec=copy.deepcopy(before)
def disk(path):return Path(u.Paths.project_content_dir())/(path.split('.')[0].removeprefix('/Game/')+'.uasset')
if hashlib.sha256(disk(equip_path).read_bytes()).hexdigest()!=read['clips']['equip']['sha256']:raise RuntimeError('Concurrent M24 equip asset change retained')
for family,p in live.items():
 if any(c.get_editor_property('retained') is not None for c in p.get_editor_property('clips')):raise RuntimeError('Retained clip requires separate merge')
 if find(before[family]['clips'],equip_path)!=find(snapshot['profiles'][family],equip_path):raise RuntimeError('Concurrent equip layer change retained')
for key,replacement in patch.items():
 family,role=key.split('/');dst=find(spec[family]['clips'],replacement['base']);expected=find(snapshot['profiles'][family],replacement['base']);start,end=replacement['window']
 for new in replacement['tracks']:
  name=new['bone'];current=next((t for t in dst['tracks'] if t['bone']==name),None);original=next((t for t in expected['tracks'] if t['bone']==name),None)
  if current!=original:raise RuntimeError('Concurrent reload contact change retained '+key+'/'+name)
  if current is None:
   current={'bone':name,'times':[0.,dst['duration']],'values':[0.,0.,0.,0.,0.,0.,1.,0.,0.,0.]*2};dst['tracks'].append(current)
  old=copy.deepcopy(current);times=list(old['times'])
  for t in new['times']:
   if start<t<end and all(abs(t-x)>1e-6 for x in times):times.append(t)
  times.sort();values=[];last=None
  for t in times:
   v=sample(new if start+1e-6<t<end-1e-6 else old,t,10,'values')
   if last and sum(a*b for a,b in zip(last,v[3:7]))<0:v[3:7]=[-q for q in v[3:7]]
   last=v[3:7];values.extend(v)
  current.update(times=times,values=values)
backup=O/'Backups';backup.mkdir(exist_ok=True)
for path in [*paths.values(),equip_path]:
 src=disk(path);dest=backup/src.name
 if not dest.exists():shutil.copy2(src,dest)
for family in before:(backup/(family+'.json')).write_text(json.dumps(before[family]))
receipt={'complete':False,'saved':[],'runtime_tested':False,'roles':['reload','reload_empty','reload_mag10','reload_empty_mag10','equip','equip_mag10']}
def record():(O/'install_receipt.json').write_text(json.dumps(receipt,indent=2))
def save(asset):
 if not E.save_loaded_asset(asset,False):raise RuntimeError('Save failed '+asset.get_path_name())
 receipt['saved'].append({'path':asset.get_path_name(),'sha256':hashlib.sha256(disk(asset.get_path_name()).read_bytes()).hexdigest()});record()
mesh=u.load_asset('/Game/Weapons/M24/MotionMagazine20261027/SK_M24_MotionV9');skeleton=mesh.skeleton
if skeleton.get_path_name().split('.')[0] in dirty:raise RuntimeError('Shared skeleton has unsaved edits')
flag='Interchange.FeatureFlags.Import.FBX';previous=u.SystemLibrary.get_console_variable_int_value(flag);u.SystemLibrary.execute_console_command(None,flag+' 0')
try:
 clips={}
 for role in ('equip','equip_mag10'):
  folder=equip_package.rsplit('/',1)[0] if role=='equip' else '/Game/Weapons/M24/GraspEquip20261028/Authoring'
  opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_ANIMATION;opt.import_mesh=False;opt.import_animations=True;opt.import_materials=False;opt.import_textures=False;opt.skeleton=skeleton
  opt.anim_sequence_import_data.set_editor_property('use_default_sample_rate',False);opt.anim_sequence_import_data.set_editor_property('custom_sample_rate',30)
  t=u.AssetImportTask();t.filename=str(O/'Export'/('A_M24_'+role+'.fbx'));t.destination_path=folder;t.destination_name='A_M24_'+role;t.automated=True;t.replace_existing=True;t.replace_existing_settings=True;t.save=False;t.factory=u.FbxFactory();t.options=opt;A.import_asset_tasks([t])
  clip=u.load_asset(folder+'/A_M24_'+role)
  if not clip:raise RuntimeError('Equip animation import failed '+role)
  clip.set_editor_property('bone_compression_settings',u.load_asset('/Game/Weapons/M4InfimaRigV4/BC_M4Viewmodel'));save(clip);clips[role]=clip
 tmp=u.new_object(u.WeaponGripProfile)
 if not tmp.bake_clip(clips['equip'],clips['equip_mag10']):raise RuntimeError('Equip mag10 layer bake failed')
 extension=packed(tmp,'mag10')['clips'][0]
 for family in spec:
  equip=find(spec[family]['clips'],equip_path);equip.update(duration=clips['equip'].get_play_length(),tracks=[] if family=='base' else extension['tracks'])
 for family,p in live.items():
  if not p.set_shared_clips_from_json(json.dumps(spec[family])):raise RuntimeError('Grip profile import failed '+family)
  save(p);(O/(family+'_profile.json')).write_text(json.dumps(packed(p,family)))
 receipt['equip_seconds']=clips['equip'].get_play_length();receipt['complete']=True;record()
finally:u.SystemLibrary.execute_console_command(None,flag+' '+str(previous))
print('M24_MAGAZINE_GRASP_EQUIP_SAVED',json.dumps(receipt),flush=True)
