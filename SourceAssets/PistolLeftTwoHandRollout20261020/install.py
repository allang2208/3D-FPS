"""Save rollout animations and sparse attachment profiles, without gameplay."""
import json,gc
from pathlib import Path
import unreal as u
O=Path('D:/FPS3D/FPSGAME/SourceAssets/PistolLeftTwoHandRollout20261020')
manifest=json.loads((O/'manifest.json').read_text());E=u.EditorAssetLibrary
receipt=dict(animations=[],profiles=[])
def save_receipt():
 (O/'saved-assets.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
for key,row in manifest['weapons'].items():
 mesh=u.load_asset(row['mesh'])
 for role,clip in row['clips'].items():
  path=clip['asset'];data=json.loads((O/clip['file']).read_text())
  seq=u.load_asset(path) if E.does_asset_exist(path) else E.duplicate_asset(clip['source'],path)
  if not seq:raise RuntimeError('Cannot create '+path)
  if seq.get_editor_property('skeleton')!=mesh.skeleton:
   if not u.WeaponAnimationAuthoring.rebind_native_animation(seq,mesh.skeleton):raise RuntimeError('Cannot bind '+path)
  ctrl=seq.get_editor_property('controller');ctrl.open_bracket('Left primary two-hand native motion',False)
  try:
   for i,bone in enumerate(row['names']):
    frames=[f[i] for f in data['frames']]
    pos=[u.Vector(*f[:3]) for f in frames];rot=[u.Quat(*f[3:7]) for f in frames];scale=[u.Vector(*f[7:10]) for f in frames]
    if not ctrl.set_bone_track_keys(bone,pos,rot,scale,False):
     ctrl.add_bone_curve(bone,False)
     if not ctrl.set_bone_track_keys(bone,pos,rot,scale,False):raise RuntimeError('Cannot write '+bone)
  finally:ctrl.close_bracket(False)
  if not u.WeaponAnimationAuthoring.finalize_authored_animation(seq):raise RuntimeError('Cannot finalize '+path)
  E.set_metadata_tag(seq,'LoneLeftAuthor','PistolLeftTwoHandRollout20261020; accepted Pit Viper method; native mechanisms')
  if not E.save_loaded_asset(seq,False):raise RuntimeError('Cannot save '+path)
  receipt['animations'].append(dict(weapon=key,role=role,asset=path,source=clip['source'],duration=data['length']))
  save_receipt();print('LONE_ROLLOUT_SAVED',key,role,flush=True)
  if len(receipt['animations'])%6==0:gc.collect();u.SystemLibrary.collect_garbage()
for row in manifest['profiles']:
 path=row['asset']
 if E.does_asset_exist(path):asset=u.load_asset(path)
 else:
  folder,name=path.rsplit('/',1);factory=u.DataAssetFactory()
  factory.set_editor_property('data_asset_class',u.WeaponGripProfile)
  asset=u.AssetToolsHelpers.get_asset_tools().create_asset(name,folder,u.WeaponGripProfile,factory)
 if not asset or not asset.set_shared_clips_from_json((O/row['file']).read_text()):raise RuntimeError('Cannot author '+path)
 if not E.save_loaded_asset(asset,False):raise RuntimeError('Cannot save '+path)
 receipt['profiles'].append(dict(asset=path,clips=row['clips']))
 save_receipt();print('LONE_ROLLOUT_PROFILE_SAVED',path,flush=True)
print('LONE_ROLLOUT_SAVE_COMPLETE',len(receipt['animations']),len(receipt['profiles']),flush=True)
