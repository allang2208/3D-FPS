"""Save fitted Sparrow/Jason sequences and their physical contact curves."""
import gzip,hashlib,json
from pathlib import Path
import unreal as u
O=Path(__file__).parent;ROOT=O.parents[1]
DEST='/Game/Characters/JasonPlayer20261003/BowSparrow20261018/AnimationsV3'
with gzip.open(O/'authored.json.gz','rt',encoding='utf-8') as f:d=json.load(f)
digest=hashlib.sha256((O/'authored.json.gz').read_bytes()).hexdigest()
lib=u.EditorAssetLibrary;mesh=u.load_asset(d['mesh'])
factory=u.AnimSequenceFactory();factory.set_editor_property('target_skeleton',mesh.skeleton);factory.set_editor_property('preview_skeletal_mesh',mesh)
receipt=dict(complete=False,clips={},source_url=d['source_url'],authoring_sha256=digest,game_run=False)
for role,c in d['clips'].items():
 name='J_SparrowBowV3_'+role;path=DEST+'/'+name
 if lib.does_asset_exist(path):
  clip=u.load_asset(path)
  if lib.get_metadata_tag(clip,'AuthoringSHA256')!=digest:raise RuntimeError('Keep existing different candidate '+path)
 else:
  clip=u.AssetToolsHelpers.get_asset_tools().create_asset(name,DEST,u.AnimSequence,factory)
  if not u.WeaponAnimationAuthoring.finalize_authored_animation(clip):raise RuntimeError('Initialize '+name)
  ctl=clip.get_editor_property('controller');frames=c['frames'];ctl.open_bracket('Fit native Sparrow bow '+role,False)
  try:
   ctl.set_frame_rate(u.FrameRate(c['rate'],1),False);ctl.set_number_of_frames(u.FrameNumber(len(frames)-1),False)
   for j,bone in enumerate(d['names']):
    ctl.add_bone_curve(bone,False);keys=[f[j] for f in frames]
    if not ctl.set_bone_track_keys(bone,[u.Vector(*t[:3]) for t in keys],[u.Quat(*t[3:7]) for t in keys],[u.Vector(*t[7:]) for t in keys],False):
     raise RuntimeError('Could not author '+bone)
   if not u.WeaponAnimationAuthoring.finalize_authored_animation(clip):raise RuntimeError('Populate '+name)
  finally:ctl.close_bracket(False)
  clip.set_preview_skeletal_mesh(mesh);clip.set_editor_property('enable_root_motion',False);clip.set_editor_property('force_root_lock',True)
  clip.set_editor_property('root_motion_root_lock',u.RootMotionRootLock.REF_POSE)
  curves=dict(c['float_curves']);curves['SparrowBowWeight']=[1.]*len(frames)
  for curve,values in curves.items():
   u.AnimationLibrary.add_curve(clip,curve)
   u.AnimationLibrary.add_float_curve_keys(clip,curve,[i/c['rate'] for i in range(len(values))],values)
  u.AnimationLibrary.add_animation_notify_track(clip,'SparrowBow')
  u.AnimationLibrary.add_animation_sync_marker(clip,'NativeSparrowBow',0.,'SparrowBow')
  for key,value in dict(ThirdPersonSource=d['provenance'],SourceAnimation=c['source'],SourceURL=d['source_url'],
   SourceRange=json.dumps(c['source_range']),AuthoringScript=d['authoring_script'],AuthoringSHA256=digest).items():lib.set_metadata_tag(clip,key,value)
  if not u.WeaponAnimationAuthoring.finalize_authored_animation(clip):raise RuntimeError('Finalize '+name)
  if not lib.save_loaded_asset(clip,False):raise RuntimeError('Save '+name)
 receipt['clips']['Bow.Sparrow.'+role]=clip.get_path_name()
 (O/'assets-saved.json').write_text(json.dumps(receipt,indent=2))
 print('SPARROW_BOW_ASSET_SAVED',role,clip.get_path_name(),flush=True)
receipt['complete']=True;(O/'assets-saved.json').write_text(json.dumps(receipt,indent=2))
print('SPARROW_BOW_ASSETS_COMPLETE',flush=True)
