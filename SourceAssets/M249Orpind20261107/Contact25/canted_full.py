from pathlib import Path
import pickle,runpy,numpy as np,json
r=Path(__file__).resolve().parent;s=runpy.run_path(str(r/'fit.py'),run_name='fit_module');results=pickle.load(open(r/'idle_fit.pkl','rb'));row=results['canted']
s['limits'][:3]=6;s['limits'][3:6]=45
fit=s['Fit'](row['old_world'],'canted',[n for n in s['data']['parts']['canted'] if 'side_mag' not in n],stride=1)
x=np.zeros(len(s['limits']));x[:6]=[-.1037,-1.2308,-2.0060,-2.8372,2.4179,33.5687]
x,_,after=fit.optimize(x,[(.25,4),(.125,2),(.0625,1),(.03125,.5)])
row.update(new_world=fit.root@fit.pose(x),parameters=x,after=after);pickle.dump(results,open(r/'idle_fit.pkl','wb'));(r/'idle_fit.json').write_text(json.dumps({f:{k:v for k,v in row.items() if k in ['before','after']} for f,row in results.items()},indent=2));print('CANTED_FULL',after,flush=True)
