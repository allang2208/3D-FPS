"""Read the project's persisted full-body death donor for offline authoring."""
import json
from pathlib import Path
import unreal as u

ROOT = Path('D:/FPS3D/FPSGAME')
OUT = ROOT/'SourceAssets/PlayerDeath20261006'
OUT.mkdir(parents=True, exist_ok=True)
cfg = json.loads((ROOT/'Content/ColdSteelData/player_body.json').read_text(encoding='utf-8-sig'))
mesh = u.load_asset(cfg['body_mesh'])
clip = u.load_asset('/Game/Characters/JasonPlayer20261003/Animations/J_MM_Death_Front_01')
ref = mesh.skeleton.get_reference_pose()
names = [str(n) for n in u.AnimPoseExtensions.get_bone_names(ref)]
component = u.new_object(u.SkeletalMeshComponent)
component.set_skeletal_mesh_asset(mesh)
parents = [names.index(str(component.get_parent_bone(n))) if str(component.get_parent_bone(n)) in names else -1 for n in names]
def pack(t):
    return [t.translation.x,t.translation.y,t.translation.z,t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w,t.scale3d.x,t.scale3d.y,t.scale3d.z]
options = u.AnimPoseEvaluationOptions()
options.optional_skeletal_mesh = mesh
options.evaluation_type = u.AnimDataEvalType.SOURCE
length = clip.get_play_length()
frames, trajectory = [], []
count = round(length*30)+1
for i in range(count):
    t = length*i/(count-1)
    pose = u.AnimPoseExtensions.get_anim_pose_at_time(clip,t,options)
    frames.append([pack(u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.LOCAL)) for n in names])
    trajectory.append(dict(t=t, **{n:pack(u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.WORLD)) for n in ['root','pelvis','head','hand_l','hand_r','foot_l','foot_r']}))
data = dict(mesh=mesh.get_path_name(),skeleton=mesh.skeleton.get_path_name(),source=clip.get_path_name(),duration=length,
    names=names,parents=parents,reference=[pack(u.AnimPoseExtensions.get_bone_pose(ref,n,u.AnimPoseSpaces.LOCAL)) for n in names],
    frames=frames,trajectory=trajectory)
(OUT/'authoring-input.json').write_text(json.dumps(data,separators=(',',':')),encoding='utf-8')
print('PLAYER_DEATH_INPUT_SAVED seconds='+str(length)+' frames='+str(count))
