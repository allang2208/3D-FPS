"""Requested review of the saved, compressed melee clips; no world or asset writes."""
from pathlib import Path
import unreal as u, math, json

OUT=Path('D:/FPS3D/FPSGAME/SourceAssets/BoundCongregateMeshy20261006/MeleeV17')
contract=json.loads((OUT/'motion_contract.json').read_text())
cdo=u.get_default_object(u.load_asset('/Game/Monsters/BoundCongregate/BP_BoundCongregate').generated_class())
options=u.AnimPoseEvaluationOptions()
options.evaluation_type=u.AnimDataEvalType.COMPRESSED
options.incorporate_root_motion_into_pose=False
options.optional_skeletal_mesh=cdo.get_editor_property('visual_mesh')
names=['body','body_front','maw','jaw_L','jaw_R']+['leg_'+s+str(i)+'_'+p for s in 'LR' for i in range(1,6) for p in ('upper','lower','foot')]
report={'sample_hz':240,'mesh':options.optional_skeletal_mesh.get_path_name(),'clips':{},'gameplay_tested':False}

def angle(a,b):
    norm=math.sqrt(sum(x*x for x in a)*sum(x*x for x in b))
    return math.degrees(2*math.acos(min(1,abs(sum(x*y for x,y in zip(a,b)))/norm)))

for role,field in [('Bite','bite_clip'),('Flurry','flurry_clip')]:
    clip=cdo.get_editor_property(field);duration=clip.get_play_length();count=round(duration*240)
    frames=[]
    for i in range(count+1):
        pose=u.AnimPoseExtensions.get_anim_pose_at_time(clip,duration*i/count,options)
        frame=[]
        for n in names:
            tf=u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.WORLD)
            p,q=tf.translation,tf.rotation
            frame.append(([p.x,p.y,p.z],[q.x,q.y,q.z,q.w]))
        frames.append(frame)
    supports=[n for n in names if n.endswith('_foot') and not(role=='Flurry' and n in ('leg_L1_foot','leg_R1_foot'))]
    metrics={}
    for k,n in enumerate(names):
        steps=[math.dist(a[k][0],b[k][0]) for a,b in zip(frames,frames[1:])]
        angles=[angle(a[k][1],b[k][1]) for a,b in zip(frames,frames[1:])]
        metrics[n]={'max_step_cm':max(steps),'max_rotation_deg':max(angles),'peak_rotation_time':(angles.index(max(angles))+1)/240,
            'closure_cm':math.dist(frames[0][k][0],frames[-1][k][0]),'closure_deg':angle(frames[0][k][1],frames[-1][k][1])}
        if n in supports:metrics[n]['support_drift_cm']=max(math.dist(f[k][0],frames[0][k][0]) for f in frames)
    lengths={}
    for side in 'LR':
        for i in range(1,6):
            for a,b in [('upper','lower'),('lower','foot')]:
                ia,ib=[names.index('leg_'+side+str(i)+'_'+p) for p in (a,b)]
                values=[math.dist(f[ia][0],f[ib][0]) for f in frames]
                lengths[side+str(i)+'_'+a]={'min_cm':min(values),'max_cm':max(values),'variation_cm':max(values)-min(values)}
    report['clips'][role]={'asset':clip.get_path_name(),'duration':duration,'bones':metrics,'segments':lengths,
        'finite':all(math.isfinite(x) for f in frames for p,q in f for x in p+q)}
    print('MELEE_V17_COMPRESSED',role,json.dumps({'duration':duration,'support_max_cm':max(metrics[n]['support_drift_cm'] for n in supports),
        'angle_max_deg':max(m['max_rotation_deg'] for m in metrics.values()),'segment_variation_max_cm':max(m['variation_cm'] for m in lengths.values())}))
report['timing_matches']=abs(cdo.get_editor_property('bite_contact_seconds')-contract['bite']['contact'])<.0001
(OUT/'Review/ue_compressed_review.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print('MELEE_V17_COMPRESSED_REVIEW_SAVED')
