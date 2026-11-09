from pathlib import Path
import pickle,gzip,json,shutil
import numpy as np
import contact_sweep
r=Path(__file__).resolve().parent
candidate=r/'candidate';candidate.mkdir(exist_ok=True)
shutil.copyfile(r/'geometry.pkl',candidate/'geometry.pkl')
names=pickle.load(open(r/'geometry.pkl','rb'))['names']
for role in ('reload','reload_empty'):
    data=pickle.load(open(r/(role+'_local.pkl'),'rb'));frames=np.asarray(data['frames'])
    with gzip.open(r.parent/'Motion'/(role+'.json.gz'),'rt') as src:tracks=json.load(src)['tracks']
    for name,rows in tracks.items():frames[:,names.index(name)]=rows
    data['frames']=frames
    with (candidate/(role+'_local.pkl')).open('wb') as dst:pickle.dump(data,dst)
contact_sweep.r=candidate
contact_sweep.run()
