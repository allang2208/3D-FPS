from pathlib import Path
import pickle
r=Path(__file__).resolve().parent;out={}
for family in ['base','vertical','canted','prism','angled']:
 part=pickle.load(open(r/(family+'_guarded.pkl'),'rb'))
 if len(part)!=2:raise RuntimeError('Incomplete return contacts: '+family)
 out.update(part)
pickle.dump(out,open(r/'guarded_world.pkl','wb'));print('CONTACT26_PROTECTED_RETURNS',len(out),flush=True)
