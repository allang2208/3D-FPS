"""Reference-led grip fit: elbow hinge frame, neutral palm, bounded finger flexion."""
import bpy,json,math,sys,itertools
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion
from mathutils.bvhtree import BVHTree
O=Path(__file__).parent;sys.path.insert(0,str(O))
from inspect_reference import setup_render
DATA=json.loads((O/'references.json').read_text());SRC=O.parent
ARM=json.loads((O/'arm_profile.json').read_text())
def frame(x,z):
 x=x.normalized();z=(z-x*x.dot(z)).normalized();return Matrix((x,z.cross(x),z)).transposed()
def solve_arm(p,rest,H,G,weight=1.0):
 # Shoulder remains near the original shoulder; elbow bends below/outside the grip.
 un,fn,hn='upperarm_l','lowerarm_l','hand_l'
 original={n:m.copy() for n,m in p.items()};A=p[un].translation.lerp(G@Vector(ARM['shoulder_in_mount_m']),weight);T=H.translation
 l1=(rest[fn].translation-rest[un].translation).length;l2=(rest[hn].translation-rest[fn].translation).length
 axis=(T-A).normalized();dist=(T-A).length
 if dist>l1+l2-.005:A+=axis*(dist-(l1+l2-.005));dist=(T-A).length
 pole=original[fn].translation.lerp(G@Vector(ARM['elbow_pole_in_mount_m']),weight)-A;pole=(pole-axis*pole.dot(axis)).normalized()
 along=(l1*l1-l2*l2+dist*dist)/(2*dist);E=A+axis*along+pole*math.sqrt(l1*l1-along*along)
 u=(E-A).normalized();v=(T-E).normalized();normal=u.cross(v).normalized()
 ref=DATA[ARM['reference']]['bones'];rp={n:Matrix(x['pose']) for n,x in ref.items()}
 ou=(rp[fn].translation-rp[un].translation).normalized();ov=(rp[hn].translation-rp[fn].translation).normalized();on=ou.cross(ov).normalized()
 U=frame(u,normal)@frame(ou,on).transposed();F=frame(v,normal)@frame(ov,on).transposed()
 p['clavicle_l'].translation+=A-p[un].translation
 old_u=(original[fn].translation-original[un].translation).normalized();old_v=(original[hn].translation-original[fn].translation).normalized()
 uq=(old_u.rotation_difference(u)@original[un].to_quaternion()).slerp(U.to_quaternion()@rp[un].to_quaternion(),weight)
 fq=(old_v.rotation_difference(v)@original[fn].to_quaternion()).slerp(F.to_quaternion()@rp[fn].to_quaternion(),weight)
 p[un]=Matrix.LocRotScale(A,uq,Vector((1,1,1)));p[fn]=Matrix.LocRotScale(E,fq,Vector((1,1,1)))
 for n in ['upperarm_twist_01_l','upperarm_twist_02_l']:
  old=p[un]@original[un].inverted()@original[n];new=p[un]@rp[un].inverted()@rp[n];p[n]=Matrix.LocRotScale(old.translation,old.to_quaternion().slerp(new.to_quaternion(),weight),Vector((1,1,1)))
 neutral=p[fn].to_quaternion()@rest[fn].to_quaternion().inverted()@rest[hn].to_quaternion()
 q=H.to_quaternion()@neutral.inverted();twist=(2*math.atan2(Vector((q.x,q.y,q.z)).dot(v),q.w)+math.pi)%(2*math.pi)-math.pi
 for n,t in zip(['lowerarm_twist_02_l','lowerarm_twist_01_l'],ARM['forearm_twist_weights']):
  m=p[fn]@rest[fn].inverted()@rest[n];old=p[fn]@original[fn].inverted()@original[n];p[n]=Matrix.LocRotScale(m.translation,old.to_quaternion().slerp(Quaternion(v,twist*t)@m.to_quaternion(),weight),Vector((1,1,1)))
 p[hn]=H
 return math.degrees(twist)
def apply(r,p,rest):
 for b in r.pose.bones:
  lr=rest[b.parent.name].inverted()@rest[b.name] if b.parent else rest[b.name]
  b.matrix_basis=lr.inverted()@(p[b.parent.name].inverted()@p[b.name] if b.parent else p[b.name])
 bpy.context.view_layer.update()
def measure(r,G,prefix):
 ob=bpy.data.objects['SK_Manny_Arms_Export'];dg=bpy.context.evaluated_depsgraph_get();e=ob.evaluated_get(dg);m=e.to_mesh();m.calc_loop_triangles();v=[e.matrix_world@x.co for x in m.vertices];groups={g.index:g.name for g in ob.vertex_groups};trees={};ids={}
 for d in ['index','middle','ring','pinky','thumb']:
  ids[d]={x.index for x in ob.data.vertices if sum(g.weight for g in x.groups if groups[g.group].startswith(d+'_') and groups[g.group].endswith('_l'))>.85}
  faces=[tuple(t.vertices) for t in m.loop_triangles if all(i in ids[d] for i in t.vertices)];trees[d]=BVHTree.FromPolygons(v,faces,all_triangles=True)
 vv=[];ff=[]
 for part in bpy.context.scene.objects:
  if not part.name.startswith(prefix):continue
  ev=part.evaluated_get(dg);mesh=ev.to_mesh();mesh.calc_loop_triangles();offset=len(vv);vv.extend([ev.matrix_world@x.co for x in mesh.vertices]);ff.extend([tuple(i+offset for i in t.vertices) for t in mesh.loop_triangles]);ev.to_mesh_clear()
 gt=BVHTree.FromPolygons(vv,ff,all_triangles=True)
 result={'self':{a+'-'+b:len(trees[a].overlap(trees[b])) for a,b in itertools.combinations(trees,2)},'grip':{d:len(t.overlap(gt)) for d,t in trees.items()},'near_mm':{d:sum(sorted(gt.find_nearest(v[i])[3] for i in ids[d])[:8])/8*1000 for d in ids},'grip_bounds':[[min((G.inverted()@v)[i] for v in vv),max((G.inverted()@v)[i] for v in vv)] for i in range(3)]}
 e.to_mesh_clear();return result

if __name__=='__main__':
 for variant,title,oldpath in [('vertical','Vertical',SRC/'VerticalGripRaised20260911/vertical'),('prism','Prism',SRC/'PrismGripContact20260911/prism')]:
  if '--' in sys.argv and variant not in sys.argv[sys.argv.index('--')+1:]:continue
  out=O/variant;out.mkdir(exist_ok=True)
  bpy.ops.wm.open_mainfile(filepath=str(oldpath/f'A_M4_{title}_idle.blend'));r=bpy.data.objects['SK_M4_Infima'];s=bpy.context.scene;s.frame_set(0);bpy.context.view_layer.update();p={b.name:b.matrix.copy() for b in r.pose.bones};rest={b.name:b.matrix_local.copy() for b in r.data.bones};r.animation_data.action=None
  fit=json.loads((oldpath/'fit_final.json').read_text());G=p['WPN_root']@Matrix(fit['grip_in_root']);pr=DATA['before_prism'];H=G@Matrix(pr['G']).inverted()@Matrix(pr['bones']['hand_l']['pose'])
  if variant=='vertical':H.translation=G@Vector((-.037,.062,-.057))
  twist=solve_arm(p,rest,H,G)
  for b in r.pose.bones:
   n=b.name
   if n.endswith('_l') and n.startswith(('index','middle','ring','pinky','thumb')):
    basis=Matrix(pr['bones'][n]['basis']);p[n]=p[b.parent.name]@rest[b.parent.name].inverted()@rest[n]@basis
  apply(r,p,rest)
  result=measure(r,G,'VG_' if variant=='vertical' else 'PH_');result['forearm_twist_deg']=twist
  (out/'initial_measure.json').write_text(json.dumps(result,indent=2));print(variant,result,flush=True)
  fit['hand_in_root']=[list(x) for x in p['WPN_root'].inverted()@H];fit['basis']={b.name:[list(x) for x in b.matrix_basis] for b in r.pose.bones if b.name.startswith(('index','middle','ring','pinky','thumb')) and b.name.endswith('_l')}
  (out/'fit_final.json').write_text(json.dumps(fit,indent=2));(out/'arm_pose.json').write_text(json.dumps({n:[list(x) for x in m] for n,m in p.items() if n.endswith('_l')},indent=2))
  bpy.ops.wm.save_as_mainfile(filepath=str(out/'Fitted.blend'));setup_render(r,G,'initial_'+variant)
