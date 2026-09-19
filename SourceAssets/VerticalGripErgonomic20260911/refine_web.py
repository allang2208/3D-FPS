import bpy,json,math,sys
from pathlib import Path
from mathutils import Matrix,Quaternion,Vector
from mathutils.bvhtree import BVHTree
O=Path(__file__).parent;sys.path.insert(0,str(O));from fit_pose import apply,solve_arm
d=O/'vertical';bpy.ops.wm.open_mainfile(filepath=str(d/'FinalFit.blend'));r=bpy.data.objects['SK_M4_Infima'];fit=json.loads((d/'fit_final.json').read_text());G=r.pose.bones['WPN_root'].matrix@Matrix(fit['grip_in_root']);H=r.pose.bones['hand_l'].matrix.copy();old={b.name:b.matrix.copy() for b in r.pose.bones};rest={b.name:b.matrix_local.copy() for b in r.data.bones};basis={b.name:b.matrix_basis.copy() for b in r.pose.bones};ob=bpy.data.objects['SK_Manny_Arms_Export'];groups={g.index:g.name for g in ob.vertex_groups};ob.data.calc_loop_triangles();dominant={v.index:max([(g.weight,groups[g.group]) for g in v.groups if groups[g.group].endswith('_l')],default=(0,''))[1] for v in ob.data.vertices};faces=[tuple(t.vertices) for t in ob.data.loop_triangles if any(dominant[i].startswith(('index','middle','ring','pinky','thumb')) for i in t.vertices)];vv=[];ff=[]
for part in bpy.context.scene.objects:
 if not part.name.startswith('VG_'):continue
 e=part.evaluated_get(bpy.context.evaluated_depsgraph_get());m=e.to_mesh();m.calc_loop_triangles();offset=len(vv);vv.extend([e.matrix_world@x.co for x in m.vertices]);ff.extend([tuple(i+offset for i in t.vertices) for t in m.loop_triangles]);e.to_mesh_clear()
gt=BVHTree.FromPolygons(vv,ff,all_triangles=True)
names=['index_01_l','index_02_l','middle_01_l','middle_02_l','ring_01_l','pinky_01_l']
def evaluate(x,detail=False):
 p={n:m.copy() for n,m in old.items()};p['hand_l']=H.copy();p['hand_l'].translation+=G.to_3x3()@Vector(x[:3])/1000
 for b in r.pose.bones:
  n=b.name
  if not n.endswith('_l') or not n.startswith(('index','middle','ring','pinky','thumb')):continue
  q=basis[n].to_quaternion()
  if n in names:q=q@Quaternion((0,0,1),math.radians(x[3+names.index(n)]))
  p[n]=p[b.parent.name]@rest[b.parent.name].inverted()@rest[n]@q.to_matrix().to_4x4()
 apply(r,p,rest);e=ob.evaluated_get(bpy.context.evaluated_depsgraph_get());m=e.to_mesh();v=[e.matrix_world@z.co for z in m.vertices];ht=BVHTree.FromPolygons(v,faces,all_triangles=True);hit=ht.overlap(gt)
 if detail:print('WEB_DETAILS',[(faces[i],[dominant[k] for k in faces[i]],[[round(c,5) for c in G.inverted()@v[k]] for k in faces[i]]) for i in sorted(set(i for i,j in hit))],flush=True)
 e.to_mesh_clear();return len(hit)*1000+sum(z*z for z in x)*.001,len(hit)
x=[0.0]*9;best=evaluate(x,True)
for step in [1,.5,.25]:
 for repeat in range(2):
  for k in range(9):
   oldx=x[k];local=(best,oldx)
   for delta in [-step,step]:
    x[k]=oldx+delta
    if abs(x[k])>4:continue
    score=evaluate(x)
    if score[0]<local[0][0]:local=(score,x[k])
   best,x[k]=local
  print('WEB_REFINE',step,best,x,flush=True)
evaluate(x,True);p={b.name:b.matrix.copy() for b in r.pose.bones};solve_arm(p,rest,p['hand_l'],G);apply(r,p,rest);fit['hand_in_root']=[list(v) for v in p['WPN_root'].inverted()@p['hand_l']];fit['basis']={n:[list(v) for v in r.pose.bones[n].matrix_basis] for n in fit['basis']};fit['web_clearance']={'parameters':x,'intersections':best[1]};(d/'fit_final.json').write_text(json.dumps(fit,indent=2));bpy.ops.wm.save_as_mainfile(filepath=str(d/'FinalFit.blend'))
