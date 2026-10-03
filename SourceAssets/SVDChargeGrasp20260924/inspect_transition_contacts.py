"""Classify source transition contacts against the retained input and review frustum."""
import bpy,json,ast,math
import numpy as np
from pathlib import Path
from mathutils.bvhtree import BVHTree
O=Path(__file__).parent
tree=ast.parse((O.parent/'SVDCompletion20260923/author_svd.py').read_text(encoding='utf-8-sig'))
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='sample'],type_ignores=[]),'<sample>','exec'))
info=json.loads((O/'authoring.json').read_text())['base/reload_empty'];bpy.ops.wm.open_mainfile(filepath=info['blend'],use_scripts=False)
r=bpy.data.objects['SK_M4_Infima'];arms=bpy.data.objects['SK_Manny_Arms_Export'];s=bpy.context.scene
acts={'after':bpy.data.actions[info['action']],'before':next(a for a in bpy.data.actions if a.name.startswith('REFERENCE_REJECTED_AKM_HOOK_'))}
group_ids={g.index for g in arms.vertex_groups if g.name.endswith('_r') and g.name.startswith(('clavicle','upperarm','lowerarm'))}
ids={v.index for v in arms.data.vertices if sum(g.weight for g in v.groups if g.group in group_ids)/max(1e-8,sum(g.weight for g in v.groups))>.90}
af=[(p.vertices[0],p.vertices[i],p.vertices[i+1]) for p in arms.data.polygons if all(v in ids for v in p.vertices) for i in range(1,len(p.vertices)-1)]
parts=[o for o in s.objects if o.name in ['SM_SVD_Body','SM_SVD_ScopeBody','SM_SVD_ScopeMount','SM_SVD_Magazine']]
def contacts(av,bv,bf,pairs):
 if not pairs:return {'pairs':0,'within_review_frustum':0}
 pairs=np.array(pairs);ta=np.array(av)[np.array(af)[pairs[:,0]]];tb=np.array(bv)[np.array(bf)[pairs[:,1]]];hit=np.zeros(len(pairs),bool);visible=hit.copy()
 for one,two in [(ta,tb),(tb,ta)]:
  e1=two[:,1]-two[:,0];e2=two[:,2]-two[:,0]
  for i in range(3):
   start=one[:,i];direction=one[:,(i+1)%3]-start;h=np.cross(direction,e2);det=np.sum(e1*h,axis=1);valid=np.abs(det)>1e-12;inv=np.zeros(len(det));inv[valid]=1/det[valid]
   v0=start-two[:,0];u=np.sum(v0*h,axis=1)*inv;q=np.cross(v0,e1);v=np.sum(direction*q,axis=1)*inv;t=np.sum(e2*q,axis=1)*inv
   mask=valid&(u>1e-5)&(v>1e-5)&(u+v<1-1e-5)&(t>1e-5)&(t<1-1e-5);point=start+t[:,None]*direction
   depth=point[:,1]+.1;tv=math.tan(math.radians(75/2))
   in_frustum=(depth>.005)&(abs(point[:,0])<tv*16/9*depth)&(abs(point[:,2]-.05)<tv*depth)
   hit|=mask;visible|=mask&in_frustum
 return {'pairs':int(hit.sum()),'within_review_frustum':int(visible.sum())}
frames=[220,224,228,232,236,240,244,248,488,492,496,500,504,508,512,515];report={}
for label,action in acts.items():
 report[label]={}
 for f in frames:
  sample(r,action,f);dg=bpy.context.evaluated_depsgraph_get();ev=arms.evaluated_get(dg);av=[ev.matrix_world@v.co for v in ev.data.vertices];bvh=BVHTree.FromPolygons(av,af,all_triangles=True);row={}
  for ob in parts:
   ev=ob.evaluated_get(dg);bv=[ev.matrix_world@v.co for v in ev.data.vertices];bf=[(p.vertices[0],p.vertices[i],p.vertices[i+1]) for p in ev.data.polygons for i in range(1,len(p.vertices)-1)]
   hits=contacts(av,bv,bf,bvh.overlap(BVHTree.FromPolygons(bv,bf,all_triangles=True)))
   if hits['pairs']:row[ob.name]=hits
  report[label][str(f)]=row
(O/'transition_contacts.json').write_text(json.dumps(report,indent=2))
print('SVD_GRASP_TRANSITION_CONTACTS',json.dumps(report),flush=True)
