from pathlib import Path
import runpy,pickle,numpy as np
r=Path(__file__).resolve().parent;n=runpy.run_path(str(r/'guard_fit.py'),run_name='native_fit');F=n['ContactFit'];data=pickle.load(open(r/'native_contacts.pkl','rb'));row=min([v for v in data if v['family']=='vertical' and '_empty' in v['path']],key=lambda x:abs(x['time']-2.985096));fit=F(row['world'],'vertical',stride=1)
class Fingers(F):
 def clip(self,x,rotate=True,translate=True):
  x=super().clip(x,False,False);x[:6]=0;return x
fit=Fingers(row['world'],'vertical',stride=1);print('NATIVE_CONTACT_BEFORE',fit.score(np.zeros(len(n['limits'])),True),flush=True);x,before,after=fit.optimize();print('NATIVE_CONTACT_AFTER',after,x.tolist(),flush=True)
