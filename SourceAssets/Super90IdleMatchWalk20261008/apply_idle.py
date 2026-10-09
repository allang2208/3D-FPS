"""Save only Super90 idle left-arm tracks and idle entries of grip profiles."""
import unreal as u,json,shutil
from pathlib import Path
O=Path(__file__).parent;P=O.parents[1];D=json.loads((O/'idle_patch.json').read_text());E=u.EditorAssetLibrary
if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():raise RuntimeError('PIE has not stopped; no assets changed.')
receipt={'revision':D['revision'],'completed':False,'saved':[],'changed_bones':D['left_bones'],'runtime_tested':False}

def record(): (O/'save_receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
def load(path):
 a=u.load_asset(path)
 if not a:raise RuntimeError('Missing '+path)
 return a

def backup(path):
 rel=path.split('.')[0].removeprefix('/Game/')+'.uasset';src=P/'Content'/rel;dst=O/'Before'/'Content'/rel
 if not dst.exists():dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst)

def save(asset):
 if not E.save_loaded_asset(asset,False):raise RuntimeError('Could not save '+asset.get_path_name())
 receipt['saved'].append(asset.get_path_name());record()

def snapshot(asset):
 data={'family':str(asset.get_editor_property('family')),'clips':[]};retained={}
 for c in asset.get_editor_property('clips'):
  base=c.get_editor_property('base').get_path_name();r=c.get_editor_property('retained')
  data['clips'].append({'base':base,'duration':float(c.get_editor_property('duration')),'tracks':[{'bone':str(t.get_editor_property('bone')),'times':list(t.get_editor_property('times')),'values':list(t.get_editor_property('values'))} for t in c.get_editor_property('tracks')]})
  if r:retained[base]=r.get_path_name()
 return data,retained

idle=load(D['idle_path']);backup(D['idle_path'])
if u.AnimationLibrary.get_num_frames(idle)!=D['frames']:raise RuntimeError('Idle source duration changed during authoring.')
profiles={}
for family,spec in D['profiles'].items():
 asset=load(spec['path']);backup(spec['path']);payload,retained=snapshot(asset)
 entry=next(c for c in payload['clips'] if c['base']==D['idle_path'])
 if D['idle_path'] in retained:raise RuntimeError('Idle acquired a retained override; no assets changed.')
 entry['tracks']=[t for t in entry['tracks'] if t['bone'] not in D['left_bones']]+[t for t in spec['idle']['tracks'] if t['bone'] in D['left_bones']]
 profiles[family]=(asset,payload,retained)
record()
controller=idle.get_editor_property('controller');controller.open_bracket('Super90 idle: preserve accepted moving left-arm hold',False)
try:
 for track in D['base_tracks']:
  keys=[track['values'][i:i+10] for i in range(0,len(track['values']),10)]
  if not controller.set_bone_track_keys(track['bone'],[u.Vector(*v[:3]) for v in keys],[u.Quat(*v[3:7]) for v in keys],[u.Vector(*v[7:10]) for v in keys],False):raise RuntimeError('Cannot write '+track['bone'])
finally:controller.close_bracket(False)
if not u.WeaponAnimationAuthoring.finalize_authored_animation(idle):raise RuntimeError('Could not finalize idle')
E.set_metadata_tag(idle,'Super90IdleLeftArmSource',D['revision']+'; installed walking left-arm hold in gun space; right arm and weapon preserved')
E.set_metadata_tag(idle,'Super90IdleAuthoringScript',str(O/'apply_idle.py'))
save(idle)
for family,(asset,payload,retained) in profiles.items():
 if not asset.set_shared_clips_from_json(json.dumps(payload)):raise RuntimeError('Could not update '+family)
 if retained:
  rows=list(asset.get_editor_property('clips'))
  for i,row in enumerate(rows):
   base=row.get_editor_property('base').get_path_name()
   if base in retained:row.set_editor_property('retained',load(retained[base]));rows[i]=row
  asset.set_editor_property('clips',rows)
 E.set_metadata_tag(asset,'Super90IdleLeftArmSource',D['revision']+'; idle uses this family walking grip; all other clips preserved')
 save(asset)
receipt['completed']=True;record()
print('SUPER90_IDLE_LEFT_ARM_SAVED',len(receipt['saved']),'assets; no gameplay test',flush=True)
