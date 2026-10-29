"""Read only: evaluate the six published V11 assets with native compression."""
import json
from pathlib import Path
import unreal as u
OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[1]
saved=json.loads((OUT/'assets-saved.json').read_text())
authoring=json.loads((OUT/'authoring.json').read_text())
config=json.loads((ROOT/'Content/ColdSteelData/player_body.json').read_text(encoding='utf-8-sig'))
def pack(t):
    return [t.translation.x,t.translation.y,t.translation.z,t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w,t.scale3d.x,t.scale3d.y,t.scale3d.z]
result={}
for label,entry in saved['bodies'].items():
    active=config if label=='jason' else config['body_variants'][label]
    mesh=u.load_asset(entry['mesh'])
    names=json.loads((OUT/(label+'-actions.json')).read_text())['names']
    options=u.AnimPoseEvaluationOptions()
    options.optional_skeletal_mesh=mesh
    options.evaluation_type=u.AnimDataEvalType.COMPRESSED
    clips={}
    for role,path in entry['clips'].items():
        previous=authoring['bodies'][label]['previous_roles'][role.removeprefix('Kukri.FullBody.')]
        if active['clips'][role] not in (path,previous):raise RuntimeError('Active route changed: '+role)
        clip=u.load_asset(path)
        if not clip or clip.get_path_name()!=path:raise RuntimeError('Missing clip '+path)
        duration=clip.get_play_length();count=round(duration*60)
        times=[duration*k/count for k in range(count+1)]
        frames=[]
        for t in times:
            pose=u.AnimPoseExtensions.get_anim_pose_at_time(clip,t,options)
            frames.append([pack(u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.WORLD)) for n in names])
        clips[role.removeprefix('Kukri.FullBody.')]=dict(asset=path,active_at_read=active['clips'][role]==path,duration=duration,times=times,world=frames)
        print('V11_PREVIEW_READ '+path,flush=True)
    result[label]=dict(mesh=entry['mesh'],names=names,clips=clips)
(OUT/'preview-compressed.json').write_text(json.dumps(result,separators=(',',':')))
print('V11_PREVIEW_READ_COMPLETE',flush=True)
