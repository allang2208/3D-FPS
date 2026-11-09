from pathlib import Path
import runpy,pickle,numpy as np,json
r=Path(__file__).resolve().parent;s=runpy.run_path(str(r/'fit.py'),run_name='fit_module');rows=pickle.load(open(r/'corrected.pkl','rb'));results={}
for (family,path),row in rows.items():
 if family=='base' or '/SideMagazine' not in path:continue
 end=3.14 if path.split('.')[0].endswith('_empty') else 3.5;fit=s['Fit'](row['world'][0],family,stride=1);out=[]
 for q in [.45,.55,.65,.75,.8,.85,.9,.925,.95,.975]:
  tm=2.76+q*(end-2.76);k=np.argmin(abs(row['times']-tm));w=row['world'][k];root=s['rigid'](w[s['ix']['WPN_root']]);points=s['skin'](np.linalg.inv(root)@w);depth,near=fit.measure(points,fit.sample);out.append([round(float(row['times'][k]),4),round(float(depth.max()),3)])
 results[family+'/'+path.split('/')[-1]]=out;print('SCAN_RETURN',family,path.split('/')[-1],out,flush=True)
(r/'scan_return.json').write_text(json.dumps(results,indent=2))
