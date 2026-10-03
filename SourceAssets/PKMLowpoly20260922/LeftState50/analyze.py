"""Measure grip contact continuity, compression, and left elbow/wrist states."""
import json
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation as R
HERE=Path(__file__).resolve().parent;IN=HERE/'Input'
manifest=json.loads((IN/'manifest.json').read_text());mesh=json.loads((IN/'Bare.json').read_text())
def unit(v):return v/np.linalg.norm(v)
def angle(a,b):return float(np.degrees(np.arccos(np.clip(unit(a)@unit(b),-1,1))))
def qangle(a,b):return float(np.degrees((R.from_quat(a)*R.from_quat(b).inv()).magnitude()))
def gun_relative(row,n):
    gun=row['WPN_root'];rot=R.from_quat(gun['q']).inv()
    return {'p':rot.apply(np.array(row[n]['p'])-gun['p']), 'q':(rot*R.from_quat(row[n]['q'])).as_quat()}
ref=mesh['bones'];f0=unit(np.array(ref['hand_l']['p'])-ref['lowerarm_l']['p'])
hand_ref=R.from_quat(ref['hand_l']['q']).inv();report={'clips':{},'transitions':{},'flags':[]}
clips={}
for entry in manifest:
    name=entry['name'];clip=json.loads((IN/(name+'.json')).read_text());clips[(entry['family'],entry['action'])]=clip
    wrist=[];elbow=[];lengths=[];step=[];compression_p=[];compression_q=[];relative=[];forearm_roll=[];previous=None
    for row,compressed in zip(clip['frames'],clip['compressed']):
        s,e,w=[np.array(row[n]['p']) for n in ['upperarm_l','lowerarm_l','hand_l']]
        wrist.append(angle((R.from_quat(row['hand_l']['q'])*hand_ref).apply(f0),w-e));elbow.append(angle(e-s,w-e))
        lengths.append([np.linalg.norm(e-s),np.linalg.norm(w-e)])
        direction=unit(e-s)
        if previous is not None:step.append(angle(direction,previous))
        previous=direction
        skin=[R.from_quat(row[n]['q'])*R.from_quat(ref[n]['q']).inv() for n in ['lowerarm_l','lowerarm_twist_01_l','lowerarm_twist_02_l']]
        forearm_roll.append(max(float(np.degrees((r*skin[0].inv()).magnitude())) for r in skin))
        for n,v in compressed.items():
            compression_p.append(float(np.linalg.norm(np.array(v['p'])-row[n]['p'])))
            compression_q.append(qangle(v['q'],row[n]['q']))
        relative.append(gun_relative(row,'hand_l'))
    lengths=np.array(lengths);reference=relative[0]
    stats={'duration':entry['duration'],'keys':entry['keys'],'revision':entry['revision'],
        'wrist_degrees':[min(wrist),max(wrist)],'max_wrist_frame':int(np.argmax(wrist)),
        'elbow_degrees':[min(elbow),max(elbow)],'length_range_cm':np.ptp(lengths,axis=0).tolist(),
        'upperarm_max_step_degrees':max(step,default=0.),'forearm_helper_max_rotation_difference':max(forearm_roll),
        'compressed_max_position_error_cm':max(compression_p),'compressed_max_rotation_error_degrees':max(compression_q),
        'hand_gun_displacement_cm':max(float(np.linalg.norm(r['p']-reference['p'])) for r in relative),
        'hand_gun_rotation_degrees':max(qangle(r['q'],reference['q']) for r in relative)}
    report['clips'][name]=stats
    if entry['action'] in ['idle','aim','fire','aim_fire'] and (stats['hand_gun_displacement_cm']>.2 or stats['hand_gun_rotation_degrees']>2.):
        report['flags'].append({'clip':name,'issue':'holding_or_fire_contact_changes','distance_cm':stats['hand_gun_displacement_cm'],'angle':stats['hand_gun_rotation_degrees']})
    if max(compression_p)>.05 or max(compression_q)>1.:
        report['flags'].append({'clip':name,'issue':'compression_error','cm':max(compression_p),'degrees':max(compression_q)})
    if not all(np.isfinite(lengths.ravel())):report['flags'].append({'clip':name,'issue':'non_finite_pose'})
for family in ['base','angled','canted','vertical','prism']:
    rows={}
    for action,baseline in [('fire','idle'),('aim_fire','aim'),('reload','idle'),('reload_empty','idle')]:
        clip=clips[(family,action)];base=clips[(family,baseline)]['frames'][0]
        for endpoint,index in [('start',0),('end',-1)]:
            current=clip['frames'][index];errors={}
            for bone in ['hand_l','lowerarm_l','upperarm_l','index_03_l','thumb_03_l','pinky_03_l']:
                a=gun_relative(current,bone);b=gun_relative(base,bone)
                errors[bone]={'cm':float(np.linalg.norm(a['p']-b['p'])),'degrees':qangle(a['q'],b['q'])}
            rows[action+'_'+endpoint]=errors
            if max(v['cm'] for v in errors.values())>.25 or max(v['degrees'] for v in errors.values())>3.:
                report['flags'].append({'family':family,'transition':action+'_'+endpoint,'issue':'endpoint_mismatch','errors':errors})
    report['transitions'][family]=rows
(HERE/'pose_audit.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps({'clips':len(report['clips']),'flags':report['flags'],
    'max_compressed_position_cm':max(v['compressed_max_position_error_cm'] for v in report['clips'].values()),
    'max_compressed_rotation_degrees':max(v['compressed_max_rotation_error_degrees'] for v in report['clips'].values())},indent=2))
