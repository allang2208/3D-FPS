"""Read the reported faulty fire assets for repair; no scene or asset changes."""
import unreal as u,json
from pathlib import Path
O=Path(__file__).parent;SA=O.parent/'RSH12SingleAction20261003';B=O.parent/'RSH12Integration20261003'
def pack(t):return [t.translation.x,t.translation.y,t.translation.z,t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w,t.scale3d.x,t.scale3d.y,t.scale3d.z]
report={}
for family in ('single','r','l'):
 donor=json.loads((B/'Donor'/family/'motion.json').read_text());recipe=json.loads((SA/family/'authoring.json').read_text())
 meshpath='/Game/Weapons/RSH12/SK_RSH12_Manny' if family=='single' else '/Game/Weapons/RSH12/Dual/'+family+'/SK_Dual_RSH12_'+family
 mesh=u.load_asset(meshpath);names=list(donor['rest']);clips={}
 jobs=[dict(kind='native_idle',asset=donor['clips']['idle']['asset'])]+[dict(kind=j['kind'],asset=j['destination']+'/'+j['name']) for j in recipe['clips']]
 for job in jobs:
  clip=u.load_asset(job['asset']);modes={}
  for mode in ('SOURCE','COMPRESSED'):
   typ=getattr(u.AnimDataEvalType,mode,None)
   if typ is None:continue
   options=u.AnimPoseEvaluationOptions();options.evaluation_type=typ;options.optional_skeletal_mesh=mesh;options.should_retarget=False
   rows=[]
   for t in ([0.] if job['kind']=='native_idle' else [0.,.025,.06,.3,.6,.99]):
    pose=u.AnimPoseExtensions.get_anim_pose_at_time(clip,t,options)
    rows.append(dict(time=t,local={n:pack(u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.LOCAL)) for n in names},
     world={n:pack(u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.WORLD)) for n in names}))
   modes[mode]=rows
  clips[job['kind']]=dict(asset=clip.get_path_name(),duration=clip.get_play_length(),modes=modes)
 report[family]=dict(mesh=mesh.get_path_name(),parents=donor['parents'],clips=clips)
 print('RSH12_FIRE_INPUT_READ',family,flush=True)
(O/'installed_before.json').write_text(json.dumps(report,separators=(',',':')),encoding='utf8')
