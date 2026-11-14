from pathlib import Path
import json,gzip,numpy as np
r=Path(__file__).resolve().parent;plan=json.loads((r/'tile-plan.json').read_text())
g=json.load(gzip.open(r/'ceramic.json.gz'));t=(np.array(g['v'])+g['origin'])[g['t']];cent=t.mean(1);slot=np.asarray(g['slot']);ids=np.zeros(len(t),dtype=bool)
for p in plan['patches']:
    ax=p['axis'];h=1-ax;a,z,b,k=p['rect']
    ids |= (np.isin(slot,[1,2,4]))&(abs(cent[:,ax]-p['plane'])<2.1)&(cent[:,h]>a-.35)&(cent[:,h]<b+.35)&(cent[:,2]>z-.32)&(cent[:,2]<k+.32)
(r/'shard-ids.json').write_text(json.dumps(np.flatnonzero(ids).tolist()),'utf8')
print(np.sum(ids))
