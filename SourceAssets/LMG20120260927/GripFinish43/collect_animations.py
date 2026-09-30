import unreal as u,json,hashlib
from pathlib import Path
O=Path(__file__).parent;P=O.parents[2];(O/'AnimationInputs').mkdir(exist_ok=True);E=u.EditorAssetLibrary
mesh=u.load_asset('/Game/Weapons/LMG201/Cover10/SK_LMG201_Cover10');names=['WPN_root','clavicle_r','upperarm_r','lowerarm_r','hand_r'];out=json.loads((O/'animation_inputs.json').read_text()) if (O/'animation_inputs.json').exists() else {}
folders=['BeltFeed08/Animations','Accessories22/Animations','Magazine24/Animations','ClothFeed33/Animations']
for folder in folders:
 for asset_file in (P/'Content/Weapons/LMG201'/folder).rglob('*.uasset'):
  path='/Game/'+asset_file.relative_to(P/'Content').with_suffix('').as_posix()
  if folder.startswith('BeltFeed08') and path.rsplit('/',1)[-1].split('.')[0] not in ['A_LMG201_'+k for k in ['idle','aim','fire','aim_fire','equip','inspect','sprint_enter','sprint_loop','sprint_exit','quick_melee']]:continue
  if path in out:continue
  clip=u.load_asset(path)
  if not isinstance(clip,u.AnimSequence):continue
  model=clip.get_editor_property('data_model_interface');count=model.get_number_of_keys();seconds=clip.get_play_length();sha=hashlib.sha256((P/'Content'/(path.split('.')[0].removeprefix('/Game/')+'.uasset')).read_bytes()).hexdigest();key=hashlib.sha1(path.encode()).hexdigest()[:12];file=O/'AnimationInputs'/(key+'.json')
  def tr(t):return [*t.translation.to_tuple(),t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w,*t.scale3d.to_tuple()]
  options=u.AnimPoseEvaluationOptions(optional_skeletal_mesh=mesh,evaluation_type=u.AnimDataEvalType.SOURCE);frames=[]
  for i in range(count):
   pose=u.AnimPoseExtensions.get_anim_pose_at_time(clip,seconds*i/max(1,count-1),options)
   frames.append({'world':[tr(u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.WORLD)) for n in names],'local':[tr(u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.LOCAL)) for n in names]})
  data={'asset':path,'sha256':sha,'frames':frames,'names':names,'fps':[model.get_frame_rate().numerator,model.get_frame_rate().denominator]};file.write_text(json.dumps(data,separators=(',',':')));out[path]={'file':str(file),'sha256':sha,'frames':count};(O/'animation_inputs.json').write_text(json.dumps(out,indent=2));print('G43_READ_CLIP',path,count,flush=True)
print('G43_ANIMATION_INPUTS',len(out),flush=True)
