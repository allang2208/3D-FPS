"""Extract the currently installed source keys for authoring the two-cut motion."""
import json
from pathlib import Path
import unreal as u
P=Path(__file__).resolve().parent
paths=json.loads((P/'source_paths.json').read_text('utf-8'))
out={}
def pack(t):
    p,q,s=t.translation,t.rotation,t.scale3d
    return {'p':[p.x,p.y,p.z],'q':[q.w,q.x,q.y,q.z],'s':[s.x,s.y,s.z]}
for name,path in paths.items():
    asset=u.load_asset(path)
    if not asset:raise RuntimeError('Missing motion source '+path)
    skeleton=asset.get_editor_property('skeleton')
    pose=u.AnimPoseExtensions.get_reference_pose(skeleton)
    names=[str(n) for n in u.AnimPoseExtensions.get_bone_names(pose)]
    options=u.AnimPoseEvaluationOptions()
    options.evaluation_type=u.AnimDataEvalType.SOURCE
    fps=240 if 'Heavy' in name else 120
    length=asset.get_play_length();count=round(length*fps)
    samples=[]
    for i in range(count+1):
        time=min(i/fps,length)
        posed=u.AnimPoseExtensions.get_anim_pose_at_time(asset,time,options)
        samples.append({'seconds':time,'bones':{n:pack(u.AnimPoseExtensions.get_bone_pose(posed,n,u.AnimPoseSpaces.LOCAL)) for n in names}})
    out[name]={'path':asset.get_path_name(),'skeleton':skeleton.get_path_name(),'seconds':length,'fps':fps,
        'markers':[{'name':str(m.marker_name),'time':m.time} for m in u.AnimationLibrary.get_animation_sync_markers(asset)],
        'samples':samples}
    print('CHIXIAO_SOURCE_EXTRACTED',name,length,flush=True)
(P/'motion_sources.json').write_text(json.dumps(out,separators=(',',':')),encoding='utf-8')
