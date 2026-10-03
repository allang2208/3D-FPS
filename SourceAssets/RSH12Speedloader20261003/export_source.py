"""Read the original 715 speedloader action as production input."""
import unreal as u,json
from pathlib import Path
O=Path(__file__).parent;G=O.parent/'RSH12Grip20261003'
def pack(t):return [*t.translation.to_tuple(),t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w,*t.scale3d.to_tuple()]
for side in ('single','r','l'):
    dest=O/('speed_'+side+'.json')
    if side=='single' and (O/'speed_source.json').exists():
        dest.write_text((O/'speed_source.json').read_text());continue
    data=json.loads((G/('native_'+side+'.json')).read_text())
    path='/Game/Weapons/DanWesson715/PalmClearance20260915/Animations/A_DW715_speed_0' if side=='single' else f'/Game/Weapons/PistolDualWield20260914/DW715/{side}/RevolverReloadFlickV6/Animations/A_Dual_DW715_{side}_speed_0'
    clip=u.load_asset(path)
    options=u.AnimPoseEvaluationOptions();options.evaluation_type=u.AnimDataEvalType.SOURCE
    options.optional_skeletal_mesh=u.load_asset(data['mesh']);options.should_retarget=False
    duration=clip.get_play_length();samples=[]
    for i in range(round(duration*120)+1):
        t=min(i/120,duration);pose=u.AnimPoseExtensions.get_anim_pose_at_time(clip,t,options)
        samples.append(dict(time=t,local={n:pack(u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.LOCAL)) for n in data['rest']},world={n:pack(u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.WORLD)) for n in data['rest']}))
    data['clips']={'speed_0':dict(asset=clip.get_path_name(),duration=duration,samples=samples)}
    dest.write_text(json.dumps(data,separators=(',',':')))
    print('RSH12_SPEED_SOURCE_SAVED',side,duration,len(samples),flush=True)
