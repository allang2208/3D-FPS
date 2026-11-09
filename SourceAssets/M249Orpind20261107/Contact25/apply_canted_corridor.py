from pathlib import Path
import pickle,json,numpy as np
r=Path(__file__).resolve().parent;file=r/'return_fit_canted.pkl';curves=pickle.load(open(file,'rb'));locks=pickle.load(open(r/'wrist_lock.pkl','rb'))
def ease(x):
 x=np.clip(x,0,1);return x*x*x*(x*(x*6-15)+10)
for key,curve in curves.items():
 if key[0]!='canted':continue
 end=3.14 if key[1].split('.')[0].endswith('_empty') else 3.5;ts=curve['times'];q=np.clip((ts-2.76)/(end-2.76),0,1);gain=ease((q-.32)/.13)*(1-ease((q-.6)/.12));blend=ease((q-.28)/.04)*(1-ease((q-.72)/.05));v=curve['values'].copy();target=np.zeros_like(v[:,:6]);target[:,:3]=np.array([3.,-1.5,-3.])[None,:]*gain[:,None];v[:,:6]=v[:,:6]*(1-blend[:,None])+target*blend[:,None];v[:,6:]*=(1-blend[:,None]);curve['values']=v;locks[key]=dict(times=ts,values=v[:,:6].copy());print('CANTED_CORRIDOR_APPLIED',key[1].split('/')[-1],float(np.linalg.norm(np.diff(v[:,:3],n=2,axis=0),axis=1).max()))
pickle.dump(curves,open(file,'wb'));pickle.dump(locks,open(r/'wrist_lock.pkl','wb'));(r/'dense_canted.json').write_text('{}')
