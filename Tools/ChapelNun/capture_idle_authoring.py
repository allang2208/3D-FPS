"""Read the nun's native reference and existing idle as inputs for a new pose."""
import json
from pathlib import Path
import unreal as u

ROOT = Path('D:/FPS3D/FPSGAME')
OUT = ROOT / 'SourceAssets/ChapelNun20261115/IdleHandsFrontR1'
OUT.mkdir(parents=True, exist_ok=True)
mesh = u.load_asset('/Game/Characters/ChapelNun20261115/Meshes/SK_Nun_Body')
idle = u.load_asset('/Game/Characters/KaitlinPlayer20261023/Motion/Animations/K_abf5f26d70_J_MM_Idle')
ref = mesh.skeleton.get_reference_pose()
names = [str(n) for n in u.AnimPoseExtensions.get_bone_names(ref)]
comp = u.new_object(u.SkeletalMeshComponent)
comp.set_skeletal_mesh_asset(mesh)
indices = {n: i for i, n in enumerate(names)}

def pack(t):
    return [t.translation.x, t.translation.y, t.translation.z,
            t.rotation.x, t.rotation.y, t.rotation.z, t.rotation.w,
            t.scale3d.x, t.scale3d.y, t.scale3d.z]

options = u.AnimPoseEvaluationOptions()
options.optional_skeletal_mesh = mesh
options.evaluation_type = u.AnimDataEvalType.COMPRESSED
options.should_retarget = False
result = dict(mesh=mesh.get_path_name(), skeleton=mesh.skeleton.get_path_name(),
              source_idle=idle.get_path_name(), names=names,
              parents=[indices.get(str(comp.get_parent_bone(n)), -1) for n in names],
              reference=[pack(u.AnimPoseExtensions.get_bone_pose(ref, n, u.AnimPoseSpaces.LOCAL)) for n in names],
              idle_samples=[])
for time in (0., .5, 1.):
    pose = u.AnimPoseExtensions.get_anim_pose_at_time(idle, min(time, idle.get_play_length()), options)
    result['idle_samples'].append([pack(u.AnimPoseExtensions.get_bone_pose(pose, n, u.AnimPoseSpaces.LOCAL)) for n in names])
(OUT / 'native_rig.json').write_text(json.dumps(result, separators=(',', ':')), encoding='utf-8')
print('NUN_IDLE_INPUTS_SAVED', len(names), flush=True)
