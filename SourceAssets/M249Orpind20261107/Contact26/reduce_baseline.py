from pathlib import Path
import pickle,numpy as np
r=Path(__file__).resolve().parent;p=r/'baseline.pkl';data=pickle.load(open(p,'rb'))
for row in data.values():
 _,ids=np.unique(np.round(row['times'],6),return_index=True);row['times']=row['times'][ids];row['world']=row['world'][ids]
pickle.dump(data,open(p,'wb'));print('CONTACT26_BASELINE_TIMES',len(data),flush=True)
