"""Read Epic Kwang's original full-body takes for Jason sword adaptation.

Asset authoring input only; no world, renderer, gameplay or source asset writes.
"""
import json
from pathlib import Path
import unreal as u

ROOT = Path('D:/FPS3D/FPSGAME')
OUT = ROOT/'SourceAssets/ThirdPersonSwordKwang20261006'
OUT.mkdir(parents=True, exist_ok=True)
BASE = '/Game/ParagonKwang/Characters/Heroes/Kwang'
mesh = u.load_asset(BASE+'/Meshes/Kwang_GDC')
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
clips = {}
selected = ['Idle', 'PrimaryAttack_A_Slow', 'PrimaryAttack_B_Slow', 'PrimaryAttack_C_Slow',
            'PrimaryAttack_D_Slow', 'PrimaryAttack_Air', 'Ability_R', 'Ability_R_Intro', 'Ability_RMB']
for name in selected:
    clip = u.load_asset(BASE+'/Animations/'+name)
    duration = clip.get_play_length()
    count = round(duration*60)+1
    frames = []
    for i in range(count):
        pose = u.AnimPoseExtensions.get_anim_pose_at_time(clip,duration*i/(count-1),options)
        frames.append([pack(u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.WORLD)) for n in names])
    clips[name] = dict(asset=clip.get_path_name(),duration=duration,frames=frames)
    print('KWANG_SOURCE '+name+' '+str(duration))
data = dict(mesh=mesh.get_path_name(),skeleton=mesh.skeleton.get_path_name(),names=names,parents=parents,
            reference=[pack(u.AnimPoseExtensions.get_bone_pose(ref,n,u.AnimPoseSpaces.WORLD)) for n in names],clips=clips)
(OUT/'original-poses.json').write_text(json.dumps(data,separators=(',',':')))
print('KWANG_SOURCE_READY bones='+str(len(names)))
