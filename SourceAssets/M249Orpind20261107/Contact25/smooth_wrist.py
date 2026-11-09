"""Broaden isolated clearance impulses; keep their safe peak configurations."""
from pathlib import Path
import pickle,json,numpy as np
from scipy.interpolate import PchipInterpolator
r=Path(__file__).resolve().parent;curves=pickle.load(open(r/'return_fit.pkl','rb'));rows=pickle.load(open(r/'corrected.pkl','rb'));locks={};report={}
def ease(v):
 v=np.clip(v,0,1);return v*v*v*(v*(v*6-15)+10)
for key,curve in curves.items():
 if key[0]=='base':continue
 row=rows[key];times=row['times'];ids=(times>=curve['times'][0])&(times<=curve['times'][-1]);ts=times[ids];values=PchipInterpolator(curve['times'],curve['values'],axis=0)(ts);original=values.copy()
 linear=np.linalg.norm(np.diff(values[:,:3],n=2,axis=0),axis=1);angular=np.linalg.norm(np.diff(values[:,3:6],n=2,axis=0),axis=1)
 if linear.max(initial=0)<=2.5 and angular.max(initial=0)<=18:continue
 for iteration in range(24):
  linear=np.linalg.norm(np.diff(values[:,:3],n=2,axis=0),axis=1);angular=np.linalg.norm(np.diff(values[:,3:6],n=2,axis=0),axis=1);severity=np.maximum(linear/1.2,angular/8.)
  if severity.max(initial=0)<=1:break
  k=int(np.argmax(severity))+1;near=np.arange(max(1,k-1),min(len(ts)-1,k+2));amplitude=np.linalg.norm(values[near,:3],axis=1)+np.linalg.norm(values[near,3:6],axis=1)/10;k=int(near[np.argmax(amplitude)])
  weight=ease(1-abs(ts-ts[k])/(5/120));target=values[k,:6].copy();values[:,:6]=values[:,:6]*(1-weight[:,None])+target*weight[:,None]
 values[0,:6]=0;values[-1,:6]=0
 curves[key]=dict(times=ts,values=values);locks[key]=dict(times=ts,values=values[:,:6].copy())
 stats=dict(linear_before_cm=float(np.linalg.norm(np.diff(original[:,:3],n=2,axis=0),axis=1).max()),linear_after_cm=float(np.linalg.norm(np.diff(values[:,:3],n=2,axis=0),axis=1).max()),angular_after_deg=float(np.linalg.norm(np.diff(values[:,3:6],n=2,axis=0),axis=1).max()));report[key[0]+'/'+key[1].split('/')[-1]]=stats;print('SMOOTH_WRIST',key[0],key[1].split('/')[-1],stats)
pickle.dump(curves,open(r/'return_fit.pkl','wb'));pickle.dump(locks,open(r/'wrist_lock.pkl','wb'));(r/'wrist_smoothing.json').write_text(json.dumps(report,indent=2))
for family in ['vertical','canted','prism','angled']:
 file=r/('return_fit_'+family+'.pkl');data=pickle.load(open(file,'rb'));changed=[]
 for key in locks:
  if key[0]==family:data[key]=curves[key];changed.append(key[0]+'/'+key[1].split('/')[-1])
 pickle.dump(data,open(file,'wb'));reportfile=r/('dense_'+family+'.json');done=json.loads(reportfile.read_text())
 for key in changed:done.pop(key,None)
 reportfile.write_text(json.dumps(done,indent=2))
