from pathlib import Path
exec(compile((Path(__file__).parent/'check_root.py').read_text().split('result=[]')[0],'check','exec'))
rows=[component(local_pose('fire',t/30)) for t in (16,23,36,42)]
results=[]
for z in (-4,-6,-8,-10,-12):
 for x in (0,2,4,6):
  for phi in (0,15,30,45,60):
   trial=[]
   try:
    for row in rows:
     a=adjust(row,phi,(x,0,z));trial.append({**evaluate(a),**stats(a)})
   except ValueError:continue
   result={'offset':[x,0,z],'phi':phi,'folds':max(v['elbow_fold_triangles'] for v in trial),'top':min(v['root_top'] or 1 for v in trial),'proximal':max(v['proximal_root_visible_vertices'] for v in trial)}
   results.append(result)
results.sort(key=lambda v:(v['folds'],v['proximal'], -v['top'],abs(v['offset'][2])))
(O/'clearance_search.json').write_text(json.dumps(results,indent=2));print('CLEARANCE_SEARCH',json.dumps(results[:12]),flush=True)
