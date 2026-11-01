import json,numpy as np
from pathlib import Path
from scipy.spatial.transform import Rotation
P=Path(__file__).resolve().parent
d=json.loads((P/'native_before.json').read_text(encoding='utf-8'))
out={}
for name,clip in d['clips'].items():
    rows=[]
    for row in clip['samples']:
        pose=row['pose'];w=pose['WPN_root'];wr=Rotation.from_quat(w['q']).inv()
        hands={}
        for s in 'lr':
            h=pose['hand_'+s];p=wr.apply(np.array(h['p'])-w['p'])/w['s']
            hands[s]={'p':p.tolist(),'r':float(np.linalg.norm(p[:2]-[-.00045,.00105])),'z':p[2],
                'q':(wr*Rotation.from_quat(h['q'])).as_quat().tolist()}
        rows.append({'t':row['t'],'hands':hands})
    out[name]=rows
(P/'native_grips.json').write_text(json.dumps(out),encoding='utf-8')
print(json.dumps({n:{s:{'radius_mm':[round(min(x['hands'][s]['r'] for x in a)*1000,2),round(max(x['hands'][s]['r'] for x in a)*1000,2)],'z_mm':[round(min(x['hands'][s]['z'] for x in a)*1000,2),round(max(x['hands'][s]['z'] for x in a)*1000,2)],'peak_time':round(max(a,key=lambda x:x['hands'][s]['r'])['t'],3)} for s in 'lr'} for n,a in out.items()},indent=2))
