"""Read complete native arm/finger poses on each shared clip's existing clock."""
import unreal as u,json
from pathlib import Path
O=Path(__file__).parent;B=O.parent/'RSH12Integration20261003'
def pack(t):return [t.translation.x,t.translation.y,t.translation.z,t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w,t.scale3d.x,t.scale3d.y,t.scale3d.z]
for family in ('single','r','l'):
 data=json.loads((B/'Donor'/family/'motion.json').read_text());mesh=u.load_asset(data['mesh']);names=list(data['rest'])
 options=u.AnimPoseEvaluationOptions();options.evaluation_type=u.AnimDataEvalType.SOURCE;options.optional_skeletal_mesh=mesh;options.should_retarget=False
 for kind,clip_data in data['clips'].items():
  clip=u.load_asset(clip_data['asset'])
  for row in clip_data['samples']:
   pose=u.AnimPoseExtensions.get_anim_pose_at_time(clip,row['time'],options)
   row['local']={n:pack(u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.LOCAL)) for n in names}
   row['world']={n:pack(u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.WORLD)) for n in names}
 (O/('native_'+family+'.json')).write_text(json.dumps(data,separators=(',',':')))
 print('RSH12_COMPLETE_CONTACT_INPUT_SAVED',family,flush=True)
