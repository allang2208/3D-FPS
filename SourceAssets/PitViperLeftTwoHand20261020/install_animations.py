"""Save new left-dominant animations only; no modification to accepted sources."""
import unreal as u,json
from pathlib import Path
O=Path('D:/FPS3D/FPSGAME/SourceAssets/PitViperLeftTwoHand20261020')
manifest=json.loads((O/'manifest.json').read_text());h=json.loads((O/'hierarchy.json').read_text())
E=u.EditorAssetLibrary;root=manifest['destination'];saved=[]
for role,row in manifest['roles'].items():
 data=json.loads((O/row['file']).read_text());path=root+'/A_PitViper_LeftTwoHand_'+role
 source=u.load_asset(data['source'])
 seq=u.load_asset(path) if E.does_asset_exist(path) else E.duplicate_asset(data['source'],path)
 if not seq:raise RuntimeError('Create '+path)
 ctrl=seq.get_editor_property('controller');ctrl.open_bracket('Pit Viper left primary / right support',False)
 try:
  for i,bone in enumerate(h['names']):
   frames=[f[i] for f in data['frames']]
   pos=[u.Vector(*f[:3]) for f in frames];rot=[u.Quat(*f[3:7]) for f in frames];scl=[u.Vector(*f[7:10]) for f in frames]
   if not ctrl.set_bone_track_keys(bone,pos,rot,scl,False):
    ctrl.add_bone_curve(bone,False)
    if not ctrl.set_bone_track_keys(bone,pos,rot,scl,False):raise RuntimeError('Write '+bone)
 finally:ctrl.close_bracket(False)
 if not u.WeaponAnimationAuthoring.finalize_authored_animation(seq):raise RuntimeError('Finalize '+path)
 E.set_metadata_tag(seq,'LeftTwoHandAuthor','PitViperLeftTwoHand20261020: V9 native anatomical hand exchange; unmirrored firearm')
 E.set_metadata_tag(seq,'LeftTwoHandSource',data['source'])
 if not E.save_loaded_asset(seq,False):raise RuntimeError('Save '+path)
 saved.append({'role':role,'asset':path,'source':data['source'],'frames':len(data['frames']),'duration':data['length']})
 (O/'saved-assets.json').write_text(json.dumps(saved,indent=2),encoding='utf-8')
 print('LEFT_TWO_HAND_SAVED',role,flush=True)
print('LEFT_TWO_HAND_COMPLETE',len(saved),flush=True)
