import bpy,json,sys,math,itertools
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion
from mathutils.bvhtree import BVHTree
O=Path(__file__).parent;sys.path.insert(0,str(O));from front_pose import apply
variant=sys.argv[sys.argv.index('--')+1];D=O/'m4'/variant
bpy.ops.wm.open_mainfile(filepath=str(D/'Fitted.blend'));r=bpy.data.objects['SK_M4_Infima'];s=bpy.context.scene;fit=json.loads((D/'fit_final.json').read_text());old={b.name:b.matrix.copy() for b in r.pose.bones};rest={b.name:b.matrix_local.copy() for b in r.data.bones};G=old['WPN_root']@Matrix(fit['grip_in_root']);H=old['hand_l'];release=json.loads((O.parent/'VerticalGripErgonomic20260911'/variant/'release_profile.json').read_text());names=list(fit['basis']);closed={n:Matrix(v).to_quaternion() for n,v in fit['basis'].items()};pip,dip=fit['front_refinement']['parameters'][4:6]
ob=bpy.data.objects['SK_Manny_Arms_Export'];ob.data.calc_loop_triangles();groups={g.index:g.name for g in ob.vertex_groups};faces={};ids={}
for digit in ['index','middle','ring','pinky','thumb']:
 ids[digit]={v.index for v in ob.data.vertices if sum(g.weight for g in v.groups if groups[g.group].startswith(digit+'_') and groups[g.group].endswith('_l'))>.85};faces[digit]=[tuple(t.vertices) for t in ob.data.loop_triangles if all(i in ids[digit] for i in t.vertices)]
solid=[]
for part in s.objects:
 if part.type!='MESH' or part==ob or part.hide_render:continue
 e=part.evaluated_get(bpy.context.evaluated_depsgraph_get());m=e.to_mesh();m.calc_loop_triangles();solid.append((part.name,BVHTree.FromPolygons([e.matrix_world@v.co for v in m.vertices],[tuple(t.vertices) for t in m.loop_triangles],all_triangles=True)));e.to_mesh_clear()
def smooth(t):t=max(0,min(1,t));return t*t*(3-2*t)
def pose_at(u,params):
 lift,angle,start,speed,root_speed,finger_delay=params;p={n:m.copy() for n,m in old.items()};p['hand_l']=H.copy();p['hand_l'].translation+=G.to_3x3()@Vector(fit['release_vector'])*smooth((u-fit['retreat_start'])/(1-fit['retreat_start']))
 finger_u=max(0,min(1,(u-finger_delay)/(1-finger_delay)));index=min(len(release)-2,int(finger_u*(len(release)-1)));lo,hi=release[index:index+2];t=(finger_u-lo['u'])/(hi['u']-lo['u'])
 for b in r.pose.bones:
  n=b.name
  if n not in names:continue
  lr=rest[b.parent.name].inverted()@rest[n];parent=p[b.parent.name]@lr
  q=Quaternion(lo['basis'][n]).slerp(Quaternion(hi['basis'][n]),t)
  if n.startswith('thumb'):
   q=closed[n].copy()
   if n=='thumb_01_l':q=parent.to_quaternion().inverted()@Quaternion((G.to_3x3()@Vector((1,0,0))).normalized(),math.radians(lift)*smooth(u*root_speed))@Quaternion((G.to_3x3()@Vector((0,0,1))).normalized(),math.radians(angle)*smooth(u*root_speed))@parent.to_quaternion()@q
   else:q=q@Quaternion((0,0,1),-math.radians(pip if n=='thumb_02_l' else dip)*smooth((u-start)*speed))
  p[n]=parent@q.to_matrix().to_4x4()
 apply(r,p,rest);return {n:list(r.pose.bones[n].matrix_basis.to_quaternion()) for n in names}
def evaluate(params,us):
 hits=0;detail=[]
 for u in us:
  pose_at(u,params);e=ob.evaluated_get(bpy.context.evaluated_depsgraph_get());m=e.to_mesh();v=[e.matrix_world@z.co for z in m.vertices];trees={d:BVHTree.FromPolygons(v,f,all_triangles=True) for d,f in faces.items()};a=sum(len(trees['thumb'].overlap(tree)) for name,tree in solid);b=sum(len(trees['thumb'].overlap(trees[n])) for n in ['index','middle','ring','pinky']);e.to_mesh_clear();hits+=a+b
  if a+b:detail.append([u,a,b])
 return hits,detail
best=None
for params in itertools.product([20,35,50,-20],[35,20,50,0],[.15,.3],[3],[20],[.06,.12]):
 score,rows=evaluate(params,sorted(set([k/36 for k in range(37)]+[k/120 for k in range(13)])))
 if best is None or score<best[0]:best=(score,params,rows);print('RELEASE_FRONT_BEST',variant,best,flush=True)
 if score==0:break
score,rows=evaluate(best[1],[k/120 for k in range(121)]);assert not any(row[1] for row in rows),(variant,best,rows)
out=[{'u':k/120,'basis':pose_at(k/120,best[1])} for k in range(121)];(D/'release_profile.json').write_text(json.dumps(out,indent=2));(D/'release_front_validation.json').write_text(json.dumps({'parameters':best[1],'samples':121,'thumb_solid_hits':sum(row[1] for row in rows),'thumb_finger_contact_samples':rows,'contact_note':'Brief thumb/index surface contact during release is reported separately from grip penetration; no rigid gun/grip intersections.'},indent=2));print('RELEASE_FRONT_PASS',variant,best[1],flush=True)
