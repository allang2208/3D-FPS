from pathlib import Path
import runpy,pickle,numpy as np
r=Path(__file__).resolve().parent;n=runpy.run_path(str(r/'guard_fit.py'),run_name='polish_probe');F=n['ContactFit'];data=pickle.load(open(r/'base_guarded.pkl','rb'))
class FingerFit(F):
 def clip(self,x,rotate=True,translate=True):
  y=super().clip(x,False,False);y[:6]=0;return y
key=next(k for k in data if 'side_reload.' in k[0]);row=data[key];fit=FingerFit(row['world'][0],'base',stride=1);peak=(0,None)
for k,t in enumerate(row['times']):
 if not 2.76<t<3.5:continue
 fit.reset(row['world'][k]);depth=fit.score(np.zeros(len(n['limits'])),True)['max_depth_cm']
 if depth>peak[0]:peak=(depth,k)
k=peak[1];fit.reset(row['world'][k]);print('FINGER_POLISH_SOURCE',row['times'][k],peak[0],flush=True)
x,before,after=fit.optimize();print('FINGER_POLISH_RESULT',after,x.tolist(),flush=True)
