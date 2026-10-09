"""Read authoring inputs for idle-only left-arm alignment; no gameplay/test run."""
import unreal as u,json
from pathlib import Path
O=Path(__file__).parent
base='/Game/Weapons/Super90/Cransh20261006/Animations/'
mesh=u.load_asset('/Game/Weapons/Super90/Cransh20261006/SK_Super90_V7')
component=u.SkeletalMeshComponent();component.set_skeletal_mesh_asset(mesh)
names=[str(component.get_bone_name(i)) for i in range(component.get_num_bones())]
parents={n:str(component.get_parent_bone(n)) for n in names}
opt=u.AnimPoseEvaluationOptions();opt.optional_skeletal_mesh=mesh;opt.should_retarget=False

def pack(t):return [*t.translation.to_tuple(),t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w,*t.scale3d.to_tuple()]
def sample(asset,time,compressed=False):
 opt.evaluation_type=u.AnimDataEvalType.COMPRESSED if compressed else u.AnimDataEvalType.SOURCE
 p=u.AnimPoseExtensions.get_anim_pose_at_time(asset,time,opt)
 return {n:pack(u.AnimPoseExtensions.get_bone_pose(p,n,u.AnimPoseSpaces.LOCAL)) for n in names}
def profile_data(asset):
 result={'path':asset.get_path_name(),'family':str(asset.get_editor_property('family')),'clips':[]}
 for c in asset.get_editor_property('clips'):
  b=c.get_editor_property('base');r=c.get_editor_property('retained')
  result['clips'].append({'base':b.get_path_name(),'duration':float(c.get_editor_property('duration')),'retained':r.get_path_name() if r else None,'tracks':[{'bone':str(t.get_editor_property('bone')),'times':list(t.get_editor_property('times')),'values':list(t.get_editor_property('values'))} for t in c.get_editor_property('tracks')]})
 return result
idle=u.load_asset(base+'A_Super90_idle');walk=u.load_asset(base+'A_Super90_walk')
if not idle or not walk:raise RuntimeError('Missing active idle/walk animation')
frames=u.AnimationLibrary.get_num_frames(idle);seconds=idle.get_play_length()
out={'names':names,'parents':parents,'idle_path':idle.get_path_name(),'walk_path':walk.get_path_name(),'frames':frames,'seconds':seconds,'walk_seconds':walk.get_play_length(),'idle_rows':[sample(idle,i*seconds/frames) for i in range(frames+1)],'walk':sample(walk,0,True),'profiles':{},'pie_active':bool(u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world())}
for f in ('vertical','canted','prism','angled'):
 a=u.load_asset('/Game/Weapons/Super90/Foregrips20261007/Profiles/DA_Super90_'+f);row=profile_data(a)
 c=next((c for c in row['clips'] if c['base']==walk.get_path_name()),None)
 if not c:raise RuntimeError('Missing walking grip '+f)
 if c['retained']:row['retained_walk']=sample(u.load_asset(c['retained']),0,True)
 out['profiles'][f]=row
(O/'inputs.json').write_text(json.dumps(out,separators=(',',':')),encoding='utf-8')
print('SUPER90_IDLE_INPUTS',frames,seconds,'profiles',len(out['profiles']),'PIE',out['pie_active'],flush=True)
