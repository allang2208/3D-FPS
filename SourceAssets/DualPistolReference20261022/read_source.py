"""Read production inputs from the installed Twinblast pack; do not edit assets."""
import json
from pathlib import Path
import unreal as u

ROOT = Path('D:/FPS3D/FPSGAME')
OUT = ROOT / 'SourceAssets/DualPistolReference20261022'
BASE = '/Game/ParagonTwinblast/Characters/Heroes/TwinBlast'
source = u.load_asset(BASE + '/Meshes/TwinBlast')
cfg = json.loads((ROOT / 'Content/ColdSteelData/player_body.json').read_text(encoding='utf-8-sig'))
target = u.load_asset(cfg['body_mesh'])

def pack(t):
    p, q, s = t.translation, t.rotation, t.scale3d
    return [p.x,p.y,p.z,q.x,q.y,q.z,q.w,s.x,s.y,s.z]

def rig(mesh):
    ref = mesh.skeleton.get_reference_pose()
    names = [str(n) for n in u.AnimPoseExtensions.get_bone_names(ref)]
    component = u.new_object(u.SkeletalMeshComponent)
    component.set_skeletal_mesh_asset(mesh)
    return dict(mesh=mesh.get_path_name(), skeleton=mesh.skeleton.get_path_name(), names=names,
        parents=[names.index(str(component.get_parent_bone(n))) if str(component.get_parent_bone(n)) in names else -1 for n in names],
        reference=[pack(u.AnimPoseExtensions.get_bone_pose(ref,n,u.AnimPoseSpaces.LOCAL)) for n in names])

data = dict(source=rig(source),target=rig(target),clips={})
options = u.AnimPoseEvaluationOptions()
options.optional_skeletal_mesh = source
options.evaluation_type = u.AnimDataEvalType.SOURCE
selected = ['Idle','Idle_Relaxed','Idle_TravelMode','Walk_Fwd','Jog_Fwd','Sprint_Fwd',
            'DoubleShot_Fire_Rt','DoubleShot_Fire_Lft','Primary_Fire_Med_A','Primary_Fire_Med_B']
for name in selected:
    clip = u.load_asset(BASE+'/Animations/'+name)
    if not isinstance(clip,u.AnimSequence):
        raise RuntimeError('Missing source '+name)
    duration = clip.get_play_length()
    frames = []
    for i in range(round(duration*30)+1):
        pose = u.AnimPoseExtensions.get_anim_pose_at_time(clip,min(i/30,duration),options)
        frames.append([pack(u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.LOCAL)) for n in data['source']['names']])
    data['clips'][name] = dict(asset=clip.get_path_name(),duration=duration,rate=30,frames=frames,
        additive=str(clip.get_editor_property('additive_anim_type')),
        markers=[dict(name=str(m.marker_name),time=m.time) for m in u.AnimationLibrary.get_animation_sync_markers(clip)])
    print('TWINBLAST_SOURCE',name,duration,len(frames),flush=True)
(OUT/'source-poses.json').write_text(json.dumps(data,separators=(',',':')),encoding='utf-8')
print('TWINBLAST_INPUTS_SAVED',source.get_path_name(),len(data['source']['names']),flush=True)
