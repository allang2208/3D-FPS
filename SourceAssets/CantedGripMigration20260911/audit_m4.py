import bpy,json,math,sys
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion
O=Path(__file__).parent;S=O.parent;OLD=S/'CantedForegrip20260911/ThumbClose'
DATA=json.loads((O/'ReferenceWorkflow/original_references.json').read_text())
ref={n:Matrix(b['pose']) for n,b in DATA['original_idle']['bones'].items()}
def frame(x,z):
 x=x.normalized();z=(z-x*x.dot(z)).normalized();return Matrix((x,z.cross(x),z)).transposed()
def smooth(x):
 x=max(0,min(1,x));return x*x*(3-2*x)
def weight(clip,f,end):
 return 1-smooth((f-(20 if clip.startswith('drum') else 9))/(8 if clip.startswith('drum') else 7))+smooth((f-(end-24))/8) if 'reload' in clip else 1
def support(p,rest,w):
 old={n:m.copy() for n,m in p.items()};un,fn,hn='upperarm_l','lowerarm_l','hand_l'
 u=(p[fn].translation-p[un].translation).normalized();v=(p[hn].translation-p[fn].translation).normalized();normal=u.cross(v).normalized()
 ou=(ref[fn].translation-ref[un].translation).normalized();ov=(ref[hn].translation-ref[fn].translation).normalized();on=ou.cross(ov).normalized()
 errors=[]
 for n,d,rd in [(un,u,ou),(fn,v,ov)]:
  q=(frame(d,normal)@frame(rd,on).transposed()).to_quaternion()@ref[n].to_quaternion()
  errors.append(math.degrees(old[n].to_quaternion().rotation_difference(q).angle))
  p[n]=Matrix.LocRotScale(old[n].translation,old[n].to_quaternion().slerp(q,w),old[n].to_scale())
 for n in ['upperarm_twist_01_l','upperarm_twist_02_l']:
  target=p[un]@ref[un].inverted()@ref[n]
  p[n]=Matrix.LocRotScale(old[n].translation,old[n].to_quaternion().slerp(target.to_quaternion(),w),old[n].to_scale())
 neutral=p[fn].to_quaternion()@rest[fn].to_quaternion().inverted()@rest[hn].to_quaternion();q=p[hn].to_quaternion()@neutral.inverted()
 twist=(2*math.atan2(Vector((q.x,q.y,q.z)).dot(v),q.w)+math.pi)%(2*math.pi)-math.pi
 for n,t in [('lowerarm_twist_02_l',.5),('lowerarm_twist_01_l',1.)]:
  m=p[fn]@rest[fn].inverted()@rest[n];q=Quaternion(v,twist*t)@m.to_quaternion()
  p[n]=Matrix.LocRotScale(old[n].translation,old[n].to_quaternion().slerp(q,w),old[n].to_scale())
 return {'upperarm_roll_error_deg':errors[0],'forearm_roll_error_deg':errors[1],'distributed_twist_deg':math.degrees(twist),'elbow_bend_deg':math.degrees(u.angle(v))}
def apply(r,p,rest):
 for b in r.pose.bones:
  lr=rest[b.parent.name].inverted()@rest[b.name] if b.parent else rest[b.name]
  b.matrix_basis=lr.inverted()@(p[b.parent.name].inverted()@p[b.name] if b.parent else p[b.name])
 bpy.context.view_layer.update()
def render(r,G,label):
 src=(O/'ReferenceWorkflow/inspect_reference.py').read_text().split("if __name__=='__main__':")[0].replace("('VG_','PH_')","('VG_','PH_','CG_')")
 ns={'__file__':str(O/'render.py')};exec(src,ns);ns['setup_render'](r,G,label)
if __name__=='__main__':
 O.mkdir(exist_ok=True)
 bpy.ops.wm.open_mainfile(filepath=str(OLD/'A_M4_Canted_idle.blend'));r=bpy.data.objects['SK_M4_Infima'];s=bpy.context.scene;s.frame_set(0)
 rest={b.name:b.matrix_local.copy() for b in r.data.bones};p={b.name:b.matrix.copy() for b in r.pose.bones}
 fit=json.loads((OLD/'fit_final.json').read_text());G=p['WPN_root']@Matrix(fit['grip_in_root'])
 render(r,G,'before');r.animation_data.action=None
 report=support(p,rest,1);apply(r,p,rest);render(r,G,'after')
 bpy.ops.wm.save_as_mainfile(filepath=str(O/'M4_Canted_Audited_Idle.blend'))
 (O/'arm_audit.json').write_text(json.dumps(report,indent=2));print('M4_ARM_AUDIT',report,flush=True)
