from pathlib import Path
exec(compile((Path(__file__).parent/'author_root.py').read_text().split('patch={};report=')[0],'author','exec'))
code=(O.parent/'M24LeftElbowReview20261028/surface_scan.py').read_text();exec(compile(code[code.index('rest_v='):code.index('samples=[]')],'surface','exec'))
result=[]
for family,role in [('base','fire'),('mag10','fire'),('base','cycle'),('mag10','cycle'),('base','reload_empty'),('mag10','reload_empty_mag10')]:
 d=ue['clips'][role]
 for i in range((d['keys']-1)*2+1):
  t=i/60;result.append({'family':family,'role':role,'time':t,'before':evaluate(component(local_pose(role,t,family))),'after':evaluate(corrected(role,t,family))})
summary={'poses':len(result),'max_elbow_folds_before':max(x['before']['elbow_fold_triangles'] for x in result),'max_elbow_folds_after':max(x['after']['elbow_fold_triangles'] for x in result),'max_left_folds_before':max(x['before']['left_arm_fold_triangles'] for x in result),'max_left_folds_after':max(x['after']['left_arm_fold_triangles'] for x in result),'worse':[x for x in result if x['after']['left_arm_fold_triangles']>x['before']['left_arm_fold_triangles']]}
(O/'root_surface_check.json').write_text(json.dumps(summary,indent=2));print('ROOT_SURFACE_CHECK',json.dumps({k:v for k,v in summary.items() if k!='worse'}),flush=True)
