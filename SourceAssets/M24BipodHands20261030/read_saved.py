"""User-requested readback of the saved bipod clips, including compression."""
import unreal as u,json,gzip,math,hashlib
from pathlib import Path
O=Path(__file__).resolve().parent;R=O/'Review';R.mkdir(exist_ok=True)
with gzip.open(O/'authored.json.gz','rt') as f:auth=json.load(f)
names=auth['names'];mesh=u.load_asset(auth['mesh'])
profile=u.load_asset('/Game/Weapons/M24/Bipod20261029/DA_M24_Bipod')
out={'names':names,'rate':240,'clips':{}};report={'clips':{},'gameplay_tested':False}
def pack(tr):
    p,q,s=tr.translation,tr.rotation,tr.scale3d
    return [p.x,p.y,p.z,q.x,q.y,q.z,q.w,s.x,s.y,s.z]
for index,family in enumerate(('base','mag10')):
    clip=profile.get_editor_property('clips')[index].get_editor_property('base')
    if not clip.get_path_name().startswith('/Game/Weapons/M24/Bipod20261029/A_M24_Bipod_'+family):
        raise RuntimeError('Wrong live clip '+family)
    opt=u.AnimPoseEvaluationOptions();opt.optional_skeletal_mesh=mesh;opt.evaluation_type=u.AnimDataEvalType.COMPRESSED;opt.evaluate_curves=True
    curve_names=list(json.loads((O/'elbow_curves.json').read_text())) if (O/'elbow_curves.json').exists() else []
    curve_times=[];curve_weights={n:[] for n in curve_names}
    rows=[];errors=[]
    for i in range(round(clip.get_play_length()*240)+1):
        t=i/240.;raw=[pack(x) for x in u.AnimationLibrary.get_bone_poses_for_time(clip,names,t,False,mesh)]
        pose=u.AnimPoseExtensions.get_anim_pose_at_time(clip,t,opt)
        compressed=[pack(u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.LOCAL)) for n in names]
        rows.append(compressed)
        curve_times.append(t)
        for n in curve_names:curve_weights[n].append(u.AnimPoseExtensions.get_curve_weight(pose,n))
        for n,a,b in zip(names,raw,compressed):
            if n.startswith('ik_'):continue
            dot=abs(sum(x*y for x,y in zip(a[3:7],b[3:7])))/math.sqrt(sum(x*x for x in a[3:7])*sum(x*x for x in b[3:7]))
            errors.append((math.dist(a[:3],b[:3]),math.degrees(2*math.acos(min(1.,dot))),t,n))
    out['clips'][family]={'frames':rows,'curve_times':curve_times,'curve_weights':curve_weights}
    report['clips'][family]={'path':clip.get_path_name(),'duration':clip.get_play_length(),
        'source_keys':clip.get_editor_property('data_model_interface').get_number_of_keys(),
        'compression_worst_position':max(errors,key=lambda x:x[0]),'compression_worst_rotation':max(errors,key=lambda x:x[1])}
    if (O/'elbow_install_receipt.json').exists():
        curve_data=json.loads((O/'elbow_curves.json').read_text());curve_results=[]
        opt.evaluate_curves=True
        for n,c in curve_data.items():
            peak=c['times'][c['values'].index(1.)]
            p=u.AnimPoseExtensions.get_anim_pose_at_time(clip,peak,opt)
            weight=u.AnimPoseExtensions.get_curve_weight(p,n)
            flag=u.AnimationLibrary.get_curve_meta_data_morph_target(mesh.skeleton,n)
            if abs(weight-1.)>.002 or not flag:raise RuntimeError('Missing live corrective curve '+n+': '+str(weight))
            curve_results.append({'name':n,'peak_weight':weight,'morph_metadata':flag})
        report['clips'][family]['elbow_curves']=curve_results
        morph_names=[m.get_name() for m in mesh.get_editor_property('morph_targets')]
        if any(n not in morph_names for n in curve_data):raise RuntimeError('Saved elbow morph missing')
        report['saved_elbow_morphs']=len(curve_data)
with gzip.open(R/'compressed.json.gz','wt') as f:json.dump(out,f)
(R/'asset_readback.json').write_text(json.dumps(report,indent=2))
print('BIPOD_SAVED_READBACK',json.dumps(report),flush=True)
