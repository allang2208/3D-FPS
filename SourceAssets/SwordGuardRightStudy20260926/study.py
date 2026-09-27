"""Read-only diagnosis of the installed V23 idle-to-guard right arm."""
import sys,json,math
from pathlib import Path
TASK=Path(__file__).parent;ROOT=TASK.parents[1];V22=ROOT/'SourceAssets/SwordGuardLeftRepair20260926'
V23=ROOT/'SourceAssets/SwordGuardPalmPush20260926'
sys.path.insert(0,str(V22))
from guard_source import *
P=TASK
def qangle(a,b):
    q=a.rotation_difference(b);return math.degrees(2*math.atan2(Vector((q.x,q.y,q.z)).length,abs(q.w)))
def local_metric(p):
    h=p['hand_r'];f=p['lowerarm_r'];u=p['upperarm_r']
    fd=(h.translation-f.translation).normalized();ud=(f.translation-u.translation).normalized()
    ref=(rest['hand_r'].translation-rest['lowerarm_r'].translation).normalized()
    hd=h.to_quaternion()@rest['hand_r'].to_quaternion().inverted()
    return {'wrist_bend_deg':math.degrees(fd.angle(hd@ref)),
        'elbow_flex_deg':180-math.degrees((-ud).angle(fd)),
        'shoulder':list(u.translation),'elbow':list(f.translation),'wrist':list(h.translation)}
report={};setup_render()
for variant in ('Standard','LongGrip'):
    data=json.loads((V22/'After'/variant/'installed.json').read_text());info=data['clips']['Guard']
    patch=json.loads((V23/'Final'/variant/'Guard_patch.json').read_text())
    poses=[]
    for i,row in enumerate(info['samples']):
        original={n:ue_matrix(v) for n,v in row['world'].items()};world={}
        for n in row['world']:
            par=data['parents'][n]
            if n in patch['edited_bones']:world[n]=world[par]@ue_matrix(patch['samples'][i]['bones'][n])
            else:world[n]=original[n]
        wrapped={n:{'p':list(m.translation),'q':list(m.to_quaternion()),'s':list(m.to_scale())} for n,m in world.items()}
        poses.append(from_ue(wrapped))
    times=[r['seconds'] for r in info['samples']];dt=times[1]-times[0]
    grip=[p['WPN_root'].inverted()@p['hand_r'] for p in poses]
    metrics_rows=[local_metric(p) for p in poses]
    angular={};linear={}
    for n in ('WPN_root','hand_r','lowerarm_r','upperarm_r','clavicle_r'):
        steps=[qangle(a[n].to_quaternion(),b[n].to_quaternion())/dt for a,b in zip(poses,poses[1:])]
        move=[(b[n].translation-a[n].translation).length/dt for a,b in zip(poses,poses[1:])]
        k=max(range(len(steps)),key=lambda j:steps[j]);j=max(range(len(move)),key=lambda j:move[j])
        angular[n]={'peak_deg_s':steps[k],'time':times[k],'total_angle_deg':qangle(poses[0][n].to_quaternion(),poses[-1][n].to_quaternion())}
        linear[n]={'peak_m_s':move[j],'time':times[j],'total_travel_cm':sum(move)*dt*100,'endpoint_offset_cm':(poses[-1][n].translation-poses[0][n].translation).length*100}
    gsteps=[qangle(a.to_quaternion(),b.to_quaternion())/dt for a,b in zip(grip,grip[1:])]
    pose_samples=[]
    for i in (0,12,24,36,48,60,72,84,96):
        pose_samples.append({'seconds':times[i],'grip_rotation_deg':qangle(grip[0].to_quaternion(),grip[i].to_quaternion()),**metrics_rows[i]})
    report[variant]={'duration':info['seconds'],'grip_total_deg':qangle(grip[0].to_quaternion(),grip[-1].to_quaternion()),
        'grip_peak_deg_s':max(gsteps),'angular':angular,'linear':linear,'samples':pose_samples}
    if variant=='Standard':
        for i in (0,24,36,48,60,72,96):render_pose(poses[i],P/f'guard_{i:03d}.jpg')
(P/'diagnosis.json').write_text(json.dumps(report,indent=2))
print('RIGHT_GUARD_STUDY_COMPLETE',flush=True)
