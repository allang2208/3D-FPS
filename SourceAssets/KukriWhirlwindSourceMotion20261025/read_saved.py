"""Read the six saved compressed takes, without starting gameplay."""
import json
from pathlib import Path
import unreal as u
OUT=Path(__file__).resolve().parent
saved=json.loads((OUT/'assets-saved.json').read_text())
if not saved.get('complete'):raise RuntimeError('Incomplete asset save')
def pack(t):
    return [t.translation.x,t.translation.y,t.translation.z,t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w,t.scale3d.x,t.scale3d.y,t.scale3d.z]
result={}
for label,entry in saved['bodies'].items():
    mesh=u.load_asset(entry['mesh'])
    options=u.AnimPoseEvaluationOptions();options.optional_skeletal_mesh=mesh;options.evaluation_type=u.AnimDataEvalType.COMPRESSED
    tracked=['pelvis','spine_03']+[n+'_'+s for s in 'lr' for n in ('clavicle','upperarm','lowerarm','hand','upperarm_twist_01','upperarm_twist_02','lowerarm_twist_01','lowerarm_twist_02','middle_01','middle_02','middle_03','foot','ball')]
    clips={}
    for role,path in entry['clips'].items():
        clip=u.load_asset(path)
        if not clip or clip.get_path_name()!=path:raise RuntimeError('Missing native clip '+path)
        duration=clip.get_play_length();times=[min(k/120.,duration) for k in range(round(duration*120)+1)]
        frames=[]
        for t in times:
            pose=u.AnimPoseExtensions.get_anim_pose_at_time(clip,t,options)
            frames.append([pack(u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.WORLD)) for n in tracked])
        clips[role.removeprefix('Kukri.FullBody.')]=dict(asset=path,duration=duration,rate=120,bones=tracked,world=frames)
        print('WHIRLWIND_COMPRESSED_READ '+path,flush=True)
    result[label]=clips
(OUT/'saved-compressed.json').write_text(json.dumps(result,separators=(',',':')))
print('WHIRLWIND_COMPRESSED_READ_COMPLETE')
