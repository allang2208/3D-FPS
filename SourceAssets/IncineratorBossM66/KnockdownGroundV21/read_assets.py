"""Read the active M66 reaction references and sampled source tracks without playing."""
from pathlib import Path
import json,unreal as u
ROOT=Path(__file__).resolve().parent;(ROOT/'Records').mkdir(exist_ok=True)
bp=u.load_asset('/Game/Monsters/IncineratorBossM66/BP_M66RigPreview');cdo=u.get_default_object(bp.generated_class())
mesh=cdo.get_editor_property('visual_mesh');bounds=mesh.get_bounds()
opt=u.AnimPoseEvaluationOptions();opt.evaluation_type=u.AnimDataEvalType.SOURCE;opt.optional_skeletal_mesh=mesh
opt.should_retarget=False;opt.extract_root_motion=False
def tr(t):return dict(p=[t.translation.x,t.translation.y,t.translation.z],q=[t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w],s=[t.scale3d.x,t.scale3d.y,t.scale3d.z])
report=dict(mesh=mesh.get_path_name(),physics=cdo.get_editor_property('reaction_physics').get_path_name(),
 bounds=dict(origin=[bounds.origin.x,bounds.origin.y,bounds.origin.z],extent=[bounds.box_extent.x,bounds.box_extent.y,bounds.box_extent.z]),
 clips={},game_run=False)
for prop in ('air_clip','land_clip','get_up_clip','idle_clip'):
 clip=cdo.get_editor_property(prop);length=clip.get_play_length()
 row=dict(path=clip.get_path_name(),seconds=length,root_lock=clip.get_editor_property('force_root_lock'),samples=[],runtime_samples=[])
 for t in (0.,length*.25,length*.5,length*.75,length):
  pose=u.AnimPoseExtensions.get_anim_pose_at_time(clip,t,opt)
  row['samples'].append(dict(time=t,bones={str(n):dict(local=tr(u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.LOCAL)),component=tr(u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.WORLD)),reference=tr(u.AnimPoseExtensions.get_ref_bone_pose(pose,n,u.AnimPoseSpaces.WORLD))) for n in u.AnimPoseExtensions.get_bone_names(pose)}))
 opt.evaluation_type=u.AnimDataEvalType.COMPRESSED;opt.should_retarget=True
 for t in (0.,length*.5,length):
  pose=u.AnimPoseExtensions.get_anim_pose_at_time(clip,t,opt)
  row['runtime_samples'].append(dict(time=t,bones={str(n):dict(local=tr(u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.LOCAL)),component=tr(u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.WORLD))) for n in u.AnimPoseExtensions.get_bone_names(pose)}))
 opt.evaluation_type=u.AnimDataEvalType.SOURCE;opt.should_retarget=False
 report['clips'][prop]=row
(ROOT/'Records/active-assets.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
u.log('M66_KNOCKDOWN_REFERENCES_READ '+report['mesh'])
