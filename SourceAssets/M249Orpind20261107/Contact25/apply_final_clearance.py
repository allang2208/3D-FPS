from pathlib import Path
import json,pickle,importlib.util,numpy as np
r=Path(__file__).resolve().parent
sp=importlib.util.spec_from_file_location('contact_motion',r/'motion.py');m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m)
backup=r/'post_before_final_clearance.pkl'
if not backup.exists():backup.write_bytes((r/'post_world.pkl').read_bytes())
data=pickle.load(open(backup,'rb'));d=json.loads((r/'final_clearance_direction.json').read_text())
key=next(k for k in data if k[0]=='canted' and '/SideMagazine' in k[1] and '_empty' in k[1]);row=data[key]
for k,t in enumerate(row['times']):
    distance=abs(t-d['source'])/.055
    if distance>=1:continue
    gain=1-float(m.ease(distance));x=np.zeros(6+len(m.params));x[:3]=np.array(d['direction_gun_local'])*d['offset_cm']*gain
    row['world'][k]=m.correct(row['world'][k],x)
pickle.dump(data,open(r/'post_world.pkl','wb'))
manifest=json.loads((r/'manifest.json').read_text());manifest['cases']=[c for c in manifest['cases'] if c['name'] in ['30_empty_canted_left','45_empty_canted_left']]
(r/'final_clearance_manifest.json').write_text(json.dumps(manifest,indent=2))
print('CONTACT25_FINAL_CLEARANCE',d,flush=True)
