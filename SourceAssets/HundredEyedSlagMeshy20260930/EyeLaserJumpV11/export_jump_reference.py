"""Extract the imported Epic Rampage jump motion for body-specific adaptation."""
import json
from pathlib import Path
import unreal as u

OUT = Path(__file__).resolve().parent
PROJECT = OUT.parents[2]
if Path(u.Paths.project_dir()).resolve() != PROJECT.resolve():
    raise RuntimeError('Wrong source project')
BASE = '/Game/ParagonRampage/Characters/Heroes/Rampage'
mesh = u.load_asset(BASE+'/Meshes/Rampage')
component = u.SkeletalMeshComponent()
component.set_skeletal_mesh_asset(mesh)
bones = [str(component.get_bone_name(i)) for i in range(component.get_num_bones())]
bones = [b for b in bones if b.startswith(('root','pelvis','spine_','neck_','head','clavicle_',
    'upperarm_','lowerarm_','hand_','thigh_','calf_','foot_','ball_'))]
options = u.AnimPoseEvaluationOptions()
options.evaluation_type = u.AnimDataEvalType.RAW
options.optional_skeletal_mesh = mesh
def transform(t):
    return dict(translation_cm=list(t.translation.to_tuple()),
        rotation_xyzw=[t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w],scale=list(t.scale3d.to_tuple()))
(OUT/'SourceMotion').mkdir(parents=True,exist_ok=True)
entries = []
for name in ('Jump_Start','Jump_Mid','Jump_Fall','Jump_End'):
    clip = u.load_asset(BASE+'/Animations/'+name)
    if not isinstance(clip,u.AnimSequence): raise RuntimeError('Source jump missing: '+name)
    seconds = clip.get_play_length()
    frames = []
    for i in range(round(seconds*60)+1):
        t = min(seconds,i/60.)
        pose = u.AnimPoseExtensions.get_anim_pose_at_time(clip,t,options)
        frames.append(dict(seconds=t,component={b:transform(u.AnimPoseExtensions.get_bone_pose(pose,b,u.AnimPoseSpaces.WORLD)) for b in bones}))
    motion = dict(asset=clip.get_path_name(),seconds=seconds,sample_hz=60,frames=frames,
        parents={b:str(component.get_parent_bone(b)) for b in bones})
    (OUT/'SourceMotion'/(name+'.json')).write_text(json.dumps(motion),encoding='utf-8')
    entries.append(dict(name=name,seconds=seconds,frames=len(frames),source=clip.get_path_name()))
    print('RAMPAGE_JUMP_SOURCE_EXPORTED '+name,flush=True)
(OUT/'jump_sources.json').write_text(json.dumps(entries,indent=2),encoding='utf-8')
