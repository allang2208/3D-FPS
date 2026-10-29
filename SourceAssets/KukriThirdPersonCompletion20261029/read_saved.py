"""Read the compressed saved assets and their actual published route, without UI."""
import json,math
from pathlib import Path
import unreal as u
OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[1]
saved=json.loads((OUT/'assets-saved.json').read_text());cfg=json.loads((ROOT/'Content/ColdSteelData/player_body.json').read_text(encoding='utf-8-sig'))
results={};checks=[]
for label in ('jason','kaitlin'):
    data=json.loads((OUT/(label+'-actions.json')).read_text());mesh=u.load_asset(data['mesh'])
    opts=u.AnimPoseEvaluationOptions();opts.optional_skeletal_mesh=mesh;opts.evaluation_type=u.AnimDataEvalType.COMPRESSED
    active=cfg if label=='jason' else cfg['body_variants'][label];result=dict(mesh=data['mesh'],names=data['names'],clips={});results[label]=result
    for role,path in saved['bodies'][label]['clips'].items():
        if active['clips'].get(role)!=path:raise RuntimeError('Published route mismatch '+label+'/'+role)
        clip=u.load_asset(path)
        if not clip or clip.get_editor_property('skeleton')!=mesh.skeleton:raise RuntimeError('Native clip mismatch '+path)
        take=data['clips'][role];length=clip.get_play_length();count=round(length*20)+1;frames=[];times=[];max_angle=0.;max_move=0.
        for k in range(count):
            # Sample exact source frames and keep the actual resulting time.
            frame=round(k*(len(take['frames'])-1)/(count-1));time=frame/120.;times.append(time)
            pose=u.AnimPoseExtensions.get_anim_pose_at_time(clip,time,opts);f=[]
            for i,name in enumerate(data['names']):
                v=u.AnimPoseExtensions.get_bone_pose(pose,name,u.AnimPoseSpaces.LOCAL)
                row=[v.translation.x,v.translation.y,v.translation.z,v.rotation.x,v.rotation.y,v.rotation.z,v.rotation.w,v.scale3d.x,v.scale3d.y,v.scale3d.z];f.append(row)
                target=take['frames'][frame][i];dot=abs(sum(row[j]*target[j] for j in range(3,7)))
                norm=math.sqrt(sum(row[j]*row[j] for j in range(3,7))*sum(target[j]*target[j] for j in range(3,7)))
                max_angle=max(max_angle,math.degrees(2*math.acos(min(1,dot/max(norm,1e-12)))))
                max_move=max(max_move,math.sqrt(sum((row[j]-target[j])**2 for j in range(3))))
            frames.append(f)
        markers={str(m.marker_name):m.time for m in u.AnimationLibrary.get_animation_sync_markers(clip)}
        result['clips'][role]=dict(asset=path,duration=length,times=times,frames=frames,markers=markers)
        check=dict(case=label+'/'+role,source_rotation_error_degrees=max_angle,source_position_error_cm=max_move,route_matches=True,skeleton_matches=True,
                   passed=max_angle<1.0 and max_move<.1 and 'NativeSwordGrip' in markers)
        checks.append(check);print('SAVED_CHECK',label,role,check,flush=True)
    (OUT/'saved-poses.json').write_text(json.dumps(results,separators=(',',':')))
(OUT/'saved-checks.json').write_text(json.dumps(dict(checks=checks,failures=sum(not c['passed'] for c in checks)),indent=2))
if any(not c['passed'] for c in checks):raise RuntimeError('Saved pose differs from authoring source')
print('KUKRI_COMPLETION_SAVED_POSES_CHECKED',len(checks),flush=True)
