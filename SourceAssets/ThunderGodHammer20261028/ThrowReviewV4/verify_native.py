"""Bounded post-fix checks from the saved sequence data model, no gameplay."""
import json,math
from pathlib import Path
from mathutils import Quaternion,Vector,Matrix
P=Path(__file__).resolve().parent
before=json.loads((P/'native-poses-before.json').read_text());after=json.loads((P/'native-poses.json').read_text())
receipt=json.loads((P/'native-read-receipt.json').read_text());rows=[]
def q(t):return Quaternion((t[6],t[3],t[4],t[5])).normalized()
def angle(a,b):
    v=math.degrees(q(a).rotation_difference(q(b)).angle);return min(v,360-v)
def matrix(t):return Matrix.LocRotScale(Vector(t[:3]),q(t),Vector(t[7:10]))
def check(name,ok,value):rows.append({'check':name,'pass':bool(ok),'value':value})
check('saved revision and native skeleton',all('ThrowRefineV5:' in v['revision'] and v['same_skeleton'] for v in receipt['poses'].values()),receipt['poses'])
for clip in after:
    names=after[clip]['names'];wi=names.index('WPN_root');a=after[clip]['frames'];b=before[clip]['frames']
    pos=max(math.dist(x[wi][:3],y[wi][:3]) for x,y in zip(a,b));rot=max(angle(x[wi],y[wi]) for x,y in zip(a,b))
    check(clip+' keeps weapon trajectory',len(a)==len(b) and pos<.002 and rot<.01,{'position_error_cm':pos,'rotation_error_deg':rot})
    ranges={}
    for side in ('l','r'):
        for first,last in [('upperarm','lowerarm'),('lowerarm','hand')]:
            i,j=names.index(first+'_'+side),names.index(last+'_'+side)
            lengths=[math.dist(f[i][:3],f[j][:3]) for f in a];ranges[first+'_'+side]=max(lengths)-min(lengths)
    check(clip+' preserves native bone lengths',max(ranges.values())<.002,ranges)
# Runtime samples WarhammerHeavy::ChargeSeconds (RuneSwordHeavyRhythm: 2.0 s).
# 1.3 s is the early overhead key, not the full-charge handoff time.
names=after['Charge']['names'];n=round(2.0*after['Charge']['fps']);a=after['Charge']['frames'][n];b=after['Release']['frames'][0]
arm=[i for i,name in enumerate(names) if name.endswith(('_l','_r'))]
pos=max(math.dist(a[i][:3],b[i][:3]) for i in arm);rot=max(angle(a[i],b[i]) for i in arm)
check('charged pose joins throw without a pose jump',pos<.002 and rot<.01,{'runtime_charge_sample_seconds':2.0,'position_error_cm':pos,'rotation_error_deg':rot})
mesh=json.loads((P/'native-mesh.json').read_text());parents={n:v['parent'] for n,v in mesh['bones'].items()}
for label,d in [('before',before),('after',after)]:
    clip=d['Release'];names=clip['names'];index={n:i for i,n in enumerate(names)};frames=clip['frames'];fps=clip['fps'];differences={}
    # .2375 is the last authored sample before the .24 projectile event.
    a=frames[57];b=frames[round(.32*fps)]
    for n in names:
        if n.endswith('_r') and n.startswith(('thumb','index','middle','ring','pinky')) and 'metacarpal' not in n:
            ia,ip=index[n],index[parents[n]]
            qa=(matrix(a[ip]).inverted()@matrix(a[ia])).to_quaternion()
            qb=(matrix(b[ip]).inverted()@matrix(b[ia])).to_quaternion()
            value=math.degrees(qa.rotation_difference(qb).angle);differences[n]=min(value,360-value)
    value={'largest_difference_to_open_pose_deg':max(differences.values()),'bone_differences':differences}
    if label=='after':check('right digits open before .24 release',max(differences.values())<.10,value)
    else:before_fingers=value
report={'checks':rows,'failed':sum(not r['pass'] for r in rows),'before_release_fingers':before_fingers,
        'native_surface_frames_reviewed':True,'runtime_corrective_morphs_evaluated':False,'gameplay_run':False}
(P/'check-receipt.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps({'failed':report['failed'],'checks':[{'check':r['check'],'pass':r['pass']} for r in rows],'previous_right_digit_error_deg':before_fingers['largest_difference_to_open_pose_deg']}),flush=True)
