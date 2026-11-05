import gzip,json
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation as R
from weapon_contact_math import bodies,palm_mount,compose,inverse,fk,read
from author_contacts import compact
W=Path(__file__).resolve().parent
male,female=bodies();mounts={s:palm_mount(male,female,s) for s in ('r','l')}
rows=read(W/'saved_readback.json');report={}
for key,row in rows.items():
    with gzip.open(W/'Tracks'/(key+'.json.gz'),'rt',encoding='utf-8') as stream:data=json.load(stream)
    if not row['markers_preserved'] or row['keys']!=data['keys'] or row['rate']!=data['rate']:
        raise RuntimeError('Timing or ownership markers changed: '+key)
    if data['kind']=='bow':
        with gzip.open(W/'Authored'/(key+'.json.gz'),'rt',encoding='utf-8') as stream:authored=json.load(stream)
        error=max(float(np.max(np.abs(np.asarray(row['curves'][n])-np.asarray(v)))) for n,v in authored['curves'].items())
        report[key]={'roles':data['roles'],'curve_value_error':error}
        continue
    skel=compact(male,data['names']);ix=skel['index']
    frames=np.asarray(data['source_frames'])[:,[data['names'].index(n) for n in skel['names']]]
    errors=[];turns=[]
    for sample in row['samples']:
        at=min(sample['time']*data['rate'][0]/data['rate'][1],len(frames)-1)
        a=int(at);b=min(a+1,len(frames)-1);alpha=at-a
        second=frames[b].copy();flip=np.sum(frames[a,:,3:7]*second[:,3:7],axis=1)<0;second[flip,3:7]*=-1
        local=frames[a]*(1-alpha)+second*alpha
        local[:,3:7]/=np.linalg.norm(local[:,3:7],axis=1)[:,None]
        world=fk(local,skel)
        expected=compose(compose(mounts['r'],compose(inverse(world[ix['hand_r'],:7]),world[ix['hand_l'],:7])),inverse(mounts['l']))
        right,left=np.asarray(sample['hands'])
        actual=compose(inverse(right),left)
        errors.append(float(np.linalg.norm(expected[:3]-actual[:3])))
        turns.append(float(np.degrees((R.from_quat(expected[3:7]).inv()*R.from_quat(actual[3:7])).magnitude())))
    report[key]={'roles':data['roles'],'compressed_contact_error_cm':max(errors),'compressed_angle_error_degrees':max(turns)}
(W/'saved_contact_report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('clips',len(report),'max compressed cm',max(r.get('compressed_contact_error_cm',0) for r in report.values()),
      'max degrees',max(r.get('compressed_angle_error_degrees',0) for r in report.values()))
for r in report.values():
    if r.get('compressed_contact_error_cm',0)>.1:print(r)
