"""Read the active native bodies and animation boundaries; no asset writes."""
import json
from pathlib import Path
import unreal as u
OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[1]
cfg=json.loads((ROOT/'Content/ColdSteelData/player_body.json').read_text(encoding='utf-8-sig'))
result={}
for label in ('jason','kaitlin'):
    active=cfg if label=='jason' else cfg['body_variants'][label]
    mesh=u.load_asset(active['body_mesh'])
    names=json.loads((ROOT/'SourceAssets/KukriDualFree3D20261029'/(label+'-actions.json')).read_text())['names']
    opts=u.AnimPoseEvaluationOptions();opts.optional_skeletal_mesh=mesh;opts.evaluation_type=u.AnimDataEvalType.COMPRESSED
    result[label]={'mesh':active['body_mesh'],'names':names,'clips':{},'previous_roles':active['clips']}
    for role in ('Kukri.FullBody.Idle','Kukri.FullBody.Pommel','Kukri.FullBody.Uppercut','Kukri.FullBody.Dual.Idle','Kukri.FullBody.Dual.Slash1','Kukri.FullBody.Dual.Slash2','Pistol.KukriCarry.Hip','Pistol.KukriCarry.Aim'):
        path=active['clips'][role];clip=u.load_asset(path);length=clip.get_play_length()
        count=round(length*60)+1
        if role in ('Pistol.KukriCarry.Hip','Pistol.KukriCarry.Aim'):count=1
        frames=[]
        for k in range(count):
            time=min(k/60,length);pose=u.AnimPoseExtensions.get_anim_pose_at_time(clip,time,opts);f=[]
            for name in names:
                v=u.AnimPoseExtensions.get_bone_pose(pose,name,u.AnimPoseSpaces.LOCAL)
                f.append([v.translation.x,v.translation.y,v.translation.z,v.rotation.x,v.rotation.y,v.rotation.z,v.rotation.w,v.scale3d.x,v.scale3d.y,v.scale3d.z])
            frames.append(f)
        markers={str(m.marker_name):m.time for m in u.AnimationLibrary.get_animation_sync_markers(clip)}
        result[label]['clips'][role]={'asset':path,'duration':length,'rate':60,'frames':frames,'markers':markers}
        print('COMPLETION_INPUT',label,role,len(frames),flush=True)
    (OUT/'inputs.json').write_text(json.dumps(result,separators=(',',':')))
