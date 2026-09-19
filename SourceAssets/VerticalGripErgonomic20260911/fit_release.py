import bpy,json,math,sys,itertools
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion
from mathutils.bvhtree import BVHTree
O=Path(__file__).parent;sys.path.insert(0,str(O));from fit_pose import apply,solve_arm
def smooth(x):x=max(0,min(1,x));return x*x*(3-2*x)
for variant in sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else ['vertical','prism']:
 d=O/variant;bpy.ops.wm.open_mainfile(filepath=str(d/'FinalFit.blend'));r=bpy.data.objects['SK_M4_Infima'];s=bpy.context.scene;fit=json.loads((d/'fit_final.json').read_text());G=r.pose.bones['WPN_root'].matrix@Matrix(fit['grip_in_root']);old={b.name:b.matrix.copy() for b in r.pose.bones};rest={b.name:b.matrix_local.copy() for b in r.data.bones};H=old['hand_l'].copy()
 if variant=='vertical' and not fit.get('clamp_clearance_applied'):
  delta=G.to_3x3()@Vector((0,0,-.002));H.translation+=delta
  for n in old:
   if n.endswith('_l') and n.startswith(('hand','index','middle','ring','pinky','thumb')):old[n].translation+=delta
  solve_arm(old,rest,H,G);apply(r,old,rest);fit['hand_in_root']=[list(x) for x in old['WPN_root'].inverted()@H];fit['clamp_clearance_applied']=True
  bpy.ops.wm.save_as_mainfile(filepath=str(d/'FinalFit.blend'));(d/'fit_final.json').write_text(json.dumps(fit,indent=2))
 ob=bpy.data.objects['SK_Manny_Arms_Export'];groups={g.index:g.name for g in ob.vertex_groups};ob.data.calc_loop_triangles();dominant={v.index:max([(g.weight,groups[g.group]) for g in v.groups if groups[g.group].endswith('_l')],default=(0,''))[1] for v in ob.data.vertices}
 hf=[tuple(t.vertices) for t in ob.data.loop_triangles if any(dominant[i].startswith(('index','middle','ring','pinky','thumb')) for i in t.vertices)];faces={}
 for digit in ['index','middle','ring','pinky','thumb']:
  ids={v.index for v in ob.data.vertices if sum(g.weight for g in v.groups if groups[g.group].startswith(digit+'_') and groups[g.group].endswith('_l'))>.85};faces[digit]=[tuple(t.vertices) for t in ob.data.loop_triangles if all(i in ids for i in t.vertices)]
 vv=[];ff=[]
 for part in s.objects:
  if not part.name.startswith('VG_' if variant=='vertical' else 'PH_'):continue
  ev=part.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=ev.to_mesh();mesh.calc_loop_triangles();offset=len(vv);vv.extend([ev.matrix_world@x.co for x in mesh.vertices]);ff.extend([tuple(i+offset for i in t.vertices) for t in mesh.loop_triangles]);ev.to_mesh_clear()
 gt=BVHTree.FromPolygons(vv,ff,all_triangles=True);closed={b.name:b.matrix_basis.copy() for b in r.pose.bones if b.name.endswith('_l') and b.name.startswith(('index','middle','ring','pinky','thumb'))}
 def pose_at(u,params):
  start,speed,x,mcp,pip,dip,thumb=params[:7];thumbx,thumby=(params[7:9] if len(params)>7 else [0,0]);opening=smooth(u*speed);retreat=smooth((u-start)/(1-start));p={n:m.copy() for n,m in old.items()};p['hand_l']=H.copy();p['hand_l'].translation+=G.to_3x3()@Vector((x,.13,-.025))*retreat
  for b in r.pose.bones:
   n=b.name
   if n not in closed:continue
   q=closed[n].to_quaternion()
   if n.startswith(('index','middle','ring','pinky')) and 'metacarpal' not in n:q=q@Quaternion((0,0,1),-math.radians([mcp,pip,dip][int(n.split('_')[1])-1])*opening)
   if n=='thumb_01_l':
    t=smooth(u*8);q=q@Quaternion((1,0,0),math.radians(thumbx)*t)@Quaternion((0,1,0),math.radians(thumby)*t)@Quaternion((0,0,1),math.radians(thumb)*t)
   p[n]=p[b.parent.name]@rest[b.parent.name].inverted()@rest[n]@q.to_matrix().to_4x4()
  apply(r,p,rest);return {n:list(r.pose.bones[n].matrix_basis.to_quaternion()) for n in closed}
 def evaluate(params,us):
  out=[]
  for u in us:
   pose_at(u,params);e=ob.evaluated_get(bpy.context.evaluated_depsgraph_get());m=e.to_mesh();v=[e.matrix_world@z.co for z in m.vertices];ht=BVHTree.FromPolygons(v,hf,all_triangles=True);hit=len(ht.overlap(gt));trees={a:BVHTree.FromPolygons(v,f,all_triangles=True) for a,f in faces.items()};selfhit=sum(len(trees[a].overlap(trees[b])) for a,b in itertools.combinations(trees,2));e.to_mesh_clear();out.append([u,hit,selfhit])
  return sum(a[1]+a[2] for a in out),out
 # Resolve the tiny web/clamp contact on the complete skinned hand, not only pure digit weights.
 if variant=='vertical' and not fit.get('full_surface_clearance'):
  origin=H.copy();static=None
  for dx,dy,dz in itertools.product([-1,0,1],[-1,0,1,2],[-1,0,1,2,3]):
   H=origin.copy();H.translation+=G.to_3x3()@Vector((dx/1000,dy/1000,dz/1000));score,rows=evaluate([.3,4,-.03,30,35,20,0],[0]);score+=math.sqrt(dx*dx+dy*dy+dz*dz)*.01
   if static is None or score<static[0]:static=(score,H.copy(),rows,[dx,dy,dz])
  H=static[1];pose_at(0,[.3,4,-.03,30,35,20,0]);old={b.name:b.matrix.copy() for b in r.pose.bones};solve_arm(old,rest,H,G);apply(r,old,rest);closed={n:r.pose.bones[n].matrix_basis.copy() for n in closed};fit['hand_in_root']=[list(x) for x in old['WPN_root'].inverted()@H];fit['full_surface_clearance']=static[3];bpy.ops.wm.save_as_mainfile(filepath=str(d/'FinalFit.blend'));print('STATIC_FULL',static[0],static[2],static[3],flush=True)
 best=None;us=sorted(set([k/36 for k in range(37)]+[.02,.04,.06,.08,.12,.18,.25,.33]))
 if variant=='vertical':
  for start,x in itertools.product([.3,.2,.4],[.05,.03,.07]):
   params=[start,4,x,30,35,20,-20,-20,20];score,rows=evaluate(params,us)
   if best is None or score<best[0]:best=(score,params,rows);print('DENSE_RELEASE_BEST',variant,score,params,flush=True)
   if score==0:break
 for thumb,tx,ty in itertools.product([-20,0,20],[-20,0,20],[-20,0,20]):
  if best is not None and best[0]==0:break
  params=[.3 if variant=='vertical' else .15,4,-.03 if variant=='vertical' else -.07,30,35,20,thumb,tx,ty];score,rows=evaluate(params,us)
  if best is None or score<best[0]:best=(score,params,rows);print('RELEASE_BEST',variant,best,flush=True)
  if score==0:break
 for step in ([10,5] if best[0]>0 else []):
  for k in [3,4,5,6,7,8]:
   for delta in [-step,step]:
    params=best[1].copy();params[k]+=delta
    if not -30<=params[k]<=70:continue
    score,rows=evaluate(params,us)
    if score<best[0]:best=(score,params,rows);print('RELEASE_REFINE',variant,best,flush=True)
 release=[]
 for k in range(101):release.append({'u':k/100,'basis':pose_at(k/100,best[1])})
 (d/'release_profile.json').write_text(json.dumps(release,indent=2));(d/'release_parameters.json').write_text(json.dumps({'score':best[0],'parameters':best[1],'samples':best[2]},indent=2));fit['release_vector']=[best[1][2],.13,-.025];fit['retreat_start']=best[1][0];(d/'fit_final.json').write_text(json.dumps(fit,indent=2));print('RELEASE_FIT_DONE',variant,best,flush=True)
