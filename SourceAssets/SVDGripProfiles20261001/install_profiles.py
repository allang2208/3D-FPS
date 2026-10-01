"""Produce four compact SVD grip profiles from the currently saved animations.
Runs after the native authoring API is built. No tests, preview or game launch.
"""
import json,hashlib,shutil
from pathlib import Path
import unreal as u
O=Path(__file__).parent
P=Path(u.Paths.project_dir()).resolve()
if P!=Path('D:/FPS3D/FPSGAME').resolve():raise RuntimeError('Wrong project')
ROOT='/Game/Weapons/SVDDragunov20260922'
DEST=ROOT+'/GripProfiles20261001'
FAMILIES=('angled','vertical','canted','prism')
KINDS=('idle','aim','fire','aim_fire','equip','reload','reload_empty','inspect','sprint_enter','sprint_loop','sprint_exit','quick_melee')
E=u.EditorAssetLibrary
rp=O/'install_receipt.json'
receipt=json.loads(rp.read_text()) if rp.exists() else {'profiles':{},'complete':False,'tested':False,'source_animations_changed':False}
def record():rp.write_text(json.dumps(receipt,indent=1),encoding='utf-8')
def disk(path):return P/'Content'/(path.split('.')[0].removeprefix('/Game/')+'.uasset')
def sha(path):return hashlib.sha256(disk(path).read_bytes()).hexdigest()
def load(path):
 a=u.load_asset(path)
 if not a:raise RuntimeError('Missing source '+path)
 return a
headless='-run=pythonscript' in u.SystemLibrary.get_command_line().lower()
dirty=set()
if not headless:
 editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
 if editor and editor.get_game_world():raise RuntimeError('PIE active; preserve session')
 dirty={p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
# Read only completed, saved source packages. The recent SVD reload-return repair
# is part of this input set, including all four attachment families.
inputs={}
for family in ('base',)+FAMILIES:
 for kind in KINDS:
  path=ROOT+('/Complete20260923/Animations/A_SVD_' if family=='base' else '/Accessories20260923/Animations/A_SVD_'+family+'_')+kind
  if path in dirty:raise RuntimeError('Unsaved source animation '+path)
  inputs[family+'/'+kind]={'path':path,'sha256':sha(path)}
for family in FAMILIES:
 path=DEST+'/DA_SVD_Grip_'+family
 if path in dirty:raise RuntimeError('Unsaved profile '+path)
 source={k:v for k,v in inputs.items() if k.startswith('base/') or k.startswith(family+'/')}
 previous=receipt['profiles'].get(family)
 if previous and previous.get('saved') and previous['sources']==source:
  if sha(path)!=previous['saved_sha256']:raise RuntimeError('Profile changed since production '+path)
  continue
 if E.does_asset_exist(path):
  asset=load(path)
  if E.get_metadata_tag(asset,'GripProfileAuthor')!='SVDGripProfiles20261001':raise RuntimeError('Unowned profile '+path)
  backup=O/'BeforeAssets'/(path.removeprefix('/Game/')+'.uasset');backup.parent.mkdir(parents=True,exist_ok=True)
  if not backup.exists():shutil.copy2(disk(path),backup)
  # BakeClip replaces each existing base entry; the reflected array is read-only.
 else:
  factory=u.DataAssetFactory();factory.set_editor_property('data_asset_class',u.WeaponGripProfile)
  asset=u.AssetToolsHelpers.get_asset_tools().create_asset('DA_SVD_Grip_'+family,DEST,u.WeaponGripProfile,factory)
 if not asset:raise RuntimeError('Profile creation failed '+family)
 asset.set_editor_property('family',family)
 for kind in KINDS:
  base=load(inputs['base/'+kind]['path']);authored=load(inputs[family+'/'+kind]['path'])
  if not asset.bake_clip(base,authored):raise RuntimeError('Cannot produce layer '+family+'/'+kind)
  print('SVD_GRIP_LAYER_AUTHORED',family,kind,flush=True)
 # Re-check input ownership immediately before publication, not an animation test.
 for spec in source.values():
  if sha(spec['path'])!=spec['sha256']:raise RuntimeError('Source changed during authoring '+spec['path'])
 E.set_metadata_tag(asset,'GripProfileAuthor','SVDGripProfiles20261001')
 E.set_metadata_tag(asset,'GripProfileSource','Current saved compressed animations; 120Hz sparse local corrections')
 if not E.save_loaded_asset(asset,False):raise RuntimeError('Save failed '+path)
 layers=list(asset.get_editor_property('clips'))
 summary=[]
 for clip in layers:
  tracks=list(clip.get_editor_property('tracks'))
  summary.append({'base':clip.get_editor_property('base').get_path_name(),
   'duration':clip.get_editor_property('duration'),'tracks':len(tracks),
   'keys':sum(len(t.get_editor_property('times')) for t in tracks),
   'bones':[str(t.get_editor_property('bone')) for t in tracks]})
 receipt['profiles'][family]={'asset':path,'saved':True,'saved_sha256':sha(path),'bytes':disk(path).stat().st_size,'sources':source,'layers':summary}
 record();print('SVD_GRIP_PROFILE_SAVED',family,flush=True)
receipt.update(complete=True,base_animation_count=12,replaced_family_animation_count=48,profile_count=4,old_animations_retained=True)
record();print('SVD_GRIP_PROFILES_COMPLETE profiles=4 base_animations=12 replaced_family_animations=48 tested=False',flush=True)
