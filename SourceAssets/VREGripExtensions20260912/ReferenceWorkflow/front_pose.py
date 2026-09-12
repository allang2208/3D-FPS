import bpy,json,math
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion
O=Path(__file__).parent
REF=json.loads((O/'ReferenceWorkflow/original_references.json').read_text())['original_idle']['bones']
RP={n:Matrix(x['pose']) for n,x in REF.items()}
def frame(x,z):
 x=x.normalized();z=(z-x*x.dot(z)).normalized();return Matrix((x,z.cross(x),z)).transposed()
def solve_arm(p,rest,H,G,w=1):
 old={n:m.copy() for n,m in p.items()};un,fn,hn='upperarm_l','lowerarm_l','hand_l';A=old[un].translation;T=H.translation
 l1=(old[fn].translation-A).length;l2=(old[hn].translation-old[fn].translation).length
 desired=(H.to_3x3()@rest[hn].to_3x3().inverted()@(rest[hn].translation-rest[fn].translation)).normalized()
 ideal=T-desired*l2;targetA=ideal+(A-ideal).normalized()*l1;A=A.lerp(targetA,.85*w)
 axis=(T-A).normalized();dist=(T-A).length
 if dist>l1+l2-.004:A+=axis*(dist-(l1+l2-.004));dist=(T-A).length
 pole=old[fn].translation-A;pole-=axis*pole.dot(axis);natural=ideal-A;natural-=axis*natural.dot(axis);pole=pole.normalized().lerp(natural.normalized(),w).normalized()
 along=(l1*l1-l2*l2+dist*dist)/(2*dist);E=A+axis*along+pole*math.sqrt(max(0,l1*l1-along*along));u=(E-A).normalized();v=(T-E).normalized();normal=u.cross(v).normalized()
 ou=(RP[fn].translation-RP[un].translation).normalized();ov=(RP[hn].translation-RP[fn].translation).normalized();on=ou.cross(ov).normalized()
 p['clavicle_l'].translation+=A-old[un].translation
 for n,d,rd in [(un,u,ou),(fn,v,ov)]:
  original_dir=(old[fn].translation-old[un].translation).normalized() if n==un else (old[hn].translation-old[fn].translation).normalized()
  q=(original_dir.rotation_difference(d)@old[n].to_quaternion()).slerp((frame(d,normal)@frame(rd,on).transposed()).to_quaternion()@RP[n].to_quaternion(),w)
  p[n]=Matrix.LocRotScale(A if n==un else E,q,old[n].to_scale())
 for n in ['upperarm_twist_01_l','upperarm_twist_02_l']:
  a=p[un]@old[un].inverted()@old[n];b=p[un]@RP[un].inverted()@RP[n];p[n]=Matrix.LocRotScale(a.translation,a.to_quaternion().slerp(b.to_quaternion(),w),a.to_scale())
 neutral=p[fn].to_quaternion()@rest[fn].to_quaternion().inverted()@rest[hn].to_quaternion();q=H.to_quaternion()@neutral.inverted();twist=(2*math.atan2(Vector((q.x,q.y,q.z)).dot(v),q.w)+math.pi)%(2*math.pi)-math.pi
 for n,t in [('lowerarm_twist_02_l',.5),('lowerarm_twist_01_l',1.)]:
  a=p[fn]@old[fn].inverted()@old[n];b=p[fn]@rest[fn].inverted()@rest[n];p[n]=Matrix.LocRotScale(a.translation,a.to_quaternion().slerp(Quaternion(v,twist*t)@b.to_quaternion(),w),a.to_scale())
 p[hn]=H
 return {'wrist_axis_bend_deg':math.degrees(v.angle(desired)),'elbow_bend_deg':math.degrees(u.angle(v)),'shoulder_delta_m':list(A-old[un].translation),'twist_deg':math.degrees(twist)}
def apply(r,p,rest):
 for b in r.pose.bones:
  lr=rest[b.parent.name].inverted()@rest[b.name] if b.parent else rest[b.name]
  b.matrix_basis=lr.inverted()@(p[b.parent.name].inverted()@p[b.name] if b.parent else p[b.name])
 bpy.context.view_layer.update()
