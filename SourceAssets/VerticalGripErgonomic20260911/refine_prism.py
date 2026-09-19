"""Keep the fitted short-handstop contact and close its finger gaps with bounded edits."""
import bpy,json,math,sys
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion
from mathutils.bvhtree import BVHTree
O=Path(__file__).parent;sys.path.insert(0,str(O));from fit_pose import apply,measure
from inspect_reference import setup_render
d=O/'prism';bpy.ops.wm.open_mainfile(filepath=str(d/'Fitted.blend'));r=bpy.data.objects['SK_M4_Infima'];s=bpy.context.scene;rest={b.name:b.matrix_local.copy() for b in r.data.bones};original={b.name:b.matrix.copy() for b in r.pose.bones};fit=json.loads((O.parent/'PrismGripContact20260911/prism/fit_final.json').read_text());G=original['WPN_root']@Matrix(fit['grip_in_root']);digits=['index','middle','ring','pinky'];ob=bpy.data.objects['SK_Manny_Arms_Export'];groups={g.index:g.name for g in ob.vertex_groups};ob.data.calc_loop_triangles();ids={};faces={}
for digit in digits+['thumb']:
 ids[digit]={v.index for v in ob.data.vertices if sum(g.weight for g in v.groups if groups[g.group].startswith(digit+'_') and groups[g.group].endswith('_l'))>.85};faces[digit]=[tuple(t.vertices) for t in ob.data.loop_triangles if all(i in ids[digit] for i in t.vertices)]
vv=[];ff=[]
for part in s.objects:
 if not part.name.startswith('PH_'):continue
 ev=part.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=ev.to_mesh();mesh.calc_loop_triangles();offset=len(vv);vv.extend([ev.matrix_world@x.co for x in mesh.vertices]);ff.extend([tuple(i+offset for i in t.vertices) for t in mesh.loop_triangles]);ev.to_mesh_clear()
gt=BVHTree.FromPolygons(vv,ff,all_triangles=True);I=G.inverted();basis={b.name:b.matrix_basis.copy() for b in r.pose.bones}
def evaluate(x):
 p={n:m.copy() for n,m in original.items()}
 for b in r.pose.bones:
  n=b.name
  if not n.endswith('_l') or not n.startswith(tuple(digits)):continue
  digit=n.split('_')[0];k=digits.index(digit);fan,flex,pip,dip=x[k*4:k*4+4];local=basis[n].copy()
  if 'metacarpal' in n:
   m=original[n].copy();rot=Quaternion(G.to_3x3().col[1],math.radians(fan));m=Matrix.LocRotScale(m.translation,rot@m.to_quaternion(),m.to_scale());p[n]=m;continue
  j=int(n.split('_')[1]);m=p[b.parent.name]@rest[b.parent.name].inverted()@rest[n]@local
  if j==1:m=Matrix.LocRotScale(m.translation,original[n].to_quaternion()@Quaternion((0,0,1),math.radians(flex)),m.to_scale())
  else:m=m@Quaternion((0,0,1),math.radians(pip if j==2 else dip)).to_matrix().to_4x4()
  p[n]=m
 apply(r,p,rest);ev=ob.evaluated_get(bpy.context.evaluated_depsgraph_get());m=ev.to_mesh();v=[ev.matrix_world@z.co for z in m.vertices];trees={a:BVHTree.FromPolygons(v,f,all_triangles=True) for a,f in faces.items()};hits=0
 for i,a in enumerate(trees):
  hits+=len(trees[a].overlap(gt))
  for b in list(trees)[i+1:]:hits+=len(trees[a].overlap(trees[b]))
 gaps=[]
 for a,b in zip(digits,digits[1:]):
  near=sorted(trees[b].find_nearest(v[i])[3] for i in ids[a]);gaps.append(sum(near[:8])/8)
 score=hits*1000+sum(abs(g-.0008)*1500 for g in gaps)+sum(z*z for z in x)*.00025
 # The upper two digits keep their existing contacts; lower digits close beneath the short body.
 for a in digits[:2]:
  near=sorted(gt.find_nearest(v[i])[3] for i in ids[a]);score+=sum(near[:8])/8*200
 ev.to_mesh_clear();return score,hits,gaps
x=[0.0]*16;best=evaluate(x)
for step in [4,2,1]:
 for k in range(16):
  old=x[k];local=(best,old)
  for delta in [-step,step]:
   x[k]=old+delta
   if abs(x[k])>12:continue
   result=evaluate(x)
   if result[0]<local[0][0]:local=(result,x[k])
  best,x[k]=local
 print('PRISM_CLOSE',step,best,x,flush=True)
evaluate(x);result=measure(r,G,'PH_');result['parameters']=x;result['objective']=best
(d/'final_measure.json').write_text(json.dumps(result,indent=2));fit['basis']={b.name:[list(v) for v in b.matrix_basis] for b in r.pose.bones if b.name.startswith(('index','middle','ring','pinky','thumb')) and b.name.endswith('_l')};(d/'fit_final.json').write_text(json.dumps(fit,indent=2));bpy.ops.wm.save_as_mainfile(filepath=str(d/'FinalFit.blend'));setup_render(r,G,'final_prism');print('PRISM_FINAL',result,flush=True)
