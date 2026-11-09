from pathlib import Path
import runpy,pickle,numpy as np,ast,json
r=Path(__file__).resolve().parent;n=runpy.run_path(str(r/'fine_fit.py'),run_name='contact_fine');F=n['FineFit'];s=n['s'];data=pickle.load(open(r/'baseline.pkl','rb'))
line=next(x for x in (r/'probe_dynamic.log').read_text().splitlines() if 'vertical side' in x);x=np.array(ast.literal_eval(line.split('parameters ')[1]));key=next(k for k in data if k[0]=='vertical' and 'side_reload_empty.' in k[1]);row=data[key];w=row['world'][np.argmin(abs(row['times']-2.985096))];fit=F(w,'vertical',stride=1);points=s['skin'](fit.pose(x));alltrees=fit.trees.copy()
for tree in alltrees:
 fit.trees=[tree];dep,_=fit.measure(points,fit.sample)
 if dep.max()<=.025:continue
 ids=np.argsort(dep)[-6:];out=[]
 for i in ids:
  native=int(s['skin_ids'][i]);weights=s['g']['weights'][native]
  out.append(dict(depth=float(dep[i]),vertex=native,point=points[i].tolist(),weights=[(s['names'][b],float(v)) for b,v in weights]))
 print('RESIDUAL_PART',tree[0],json.dumps(out),flush=True)
