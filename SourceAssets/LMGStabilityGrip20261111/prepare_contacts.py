from pathlib import Path
import json,sys,numpy as np
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'M249Orpind20261107/Wrist33'))
from pose import matrix,compose,layer,rot
data=json.loads((HERE/'inputs.json').read_text());out={}
for key in ['M249','LMG201','PKM']:
    d=data[key];out[key]={}
    for family,p in d['profiles'].items():
        c=next(c for c in p['clips'] if c['base']==d['idle'])
        a=np.array([c.get('retained_idle',d['local'])])
        if not c['retained']:a=layer(a,d['idle'],p,d['names'],np.array([0.]))
        w=compose(a,d['parents'])[0];i={n:j for j,n in enumerate(d['names'])}
        h=np.linalg.inv(w[i['WPN_root']])@w[i['hand_l']];h[:3,3]*=100;h[:3,:3]=rot(h)
        out[key][family]=dict(hand_root=h.tolist(),local=a[0].tolist(),world=w.tolist())
(HERE/'contacts.json').write_text(json.dumps(out))
