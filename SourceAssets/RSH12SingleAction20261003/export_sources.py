"""Read installed native poses for single-action authoring; no asset changes."""
import unreal as u,json
from pathlib import Path
O=Path(__file__).parent
B=O.parent/'RSH12Integration20261003'
def pack(t):
    return [t.translation.x,t.translation.y,t.translation.z,t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w,t.scale3d.x,t.scale3d.y,t.scale3d.z]
for family in ('single','r','l'):
    donor=json.loads((B/'Donor'/family/'motion.json').read_text(encoding='utf8'))
    mesh=u.load_asset(donor['mesh']); names=list(donor['rest'])
    options=u.AnimPoseEvaluationOptions();options.evaluation_type=u.AnimDataEvalType.SOURCE
    options.optional_skeletal_mesh=mesh;options.should_retarget=False
    result=dict(rest=donor['rest'],parents=donor['parents'],skeleton=donor['skeleton'],clips={})
    for kind in (('idle','aim','fire','aim_fire') if family=='single' else ('idle','fire')):
        clip=u.load_asset(donor['clips'][kind]['asset'])
        if not clip:raise RuntimeError('Missing source '+kind)
        rows=[];duration=clip.get_play_length()
        steps=round(duration*60) if 'fire' in kind else 0
        for i in range(steps+1):
            t=duration*i/steps if steps else 0
            pose=u.AnimPoseExtensions.get_anim_pose_at_time(clip,t,options)
            rows.append(dict(time=t,local={n:pack(u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.LOCAL)) for n in names}))
        result['clips'][kind]=dict(asset=clip.get_path_name(),duration=duration,samples=rows)
    (O/(family+'_sources.json')).write_text(json.dumps(result,separators=(',',':')),encoding='utf8')
    print('RSH12_SINGLE_ACTION_SOURCE_SAVED',family,flush=True)
