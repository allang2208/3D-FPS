from pathlib import Path
exec(compile((Path(__file__).parent/'library.py').read_text(),'library','exec'))
final={role:[{n:Matrix(m) for n,m in row.items()} for row in rows] for role,rows in json.loads((OUT/'final_poses.json').read_text()).items()}
owned=[f'{d}_03_r' for d in ('thumb','index','middle','ring','pinky')]
ix=np.where(np.isin(dominant,[names.index(n) for n in owned]))[0][::3]
report={'samples':[],'worst_owned_penetration_mm':0.,'runtime_tested':False}
for f in np.arange(12.,44.,.5):
 a=int(f);w=float(f-a)
 row={}
 for n in names:
  x=final['fire'][a];y=final['fire'][a+1]
  la=x[parents[n]].inverted()@x[n] if parents[n] else x[n];lb=y[parents[n]].inverted()@y[n] if parents[n] else y[n]
  loc=Matrix.LocRotScale(la.translation.lerp(lb.translation,w),la.to_quaternion().slerp(lb.to_quaternion(),w),la.to_scale().lerp(lb.to_scale(),w))
  row[n]=row[parents[n]]@loc if parents[n] else loc
 data=actual(row,points(row)[ix],True);hits={}
 for p,ds in data.items():
  pen=float(max(0,-ds.min())*1000);report['worst_owned_penetration_mm']=max(report['worst_owned_penetration_mm'],pen)
  if pen>.5:hits[p]={'mm':round(pen,3),'bones':sorted(set(names[int(dominant[i])] for i,d in zip(ix,ds) if d<-.0005))}
 if hits:report['samples'].append({'frame':float(f),'overlap':hits})
(OUT/'intermediate_review.json').write_text(json.dumps(report,indent=2));print('M24_MIDFRAME_CONTACT',json.dumps(report),flush=True)
