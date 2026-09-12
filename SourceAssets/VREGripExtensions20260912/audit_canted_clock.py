import bpy,sys,json,math
from pathlib import Path
from mathutils import Matrix,Vector
sys.path.insert(0,str(Path(__file__).parent));from case import *
sys.path.insert(0,str(O/'ReferenceWorkflow'));import front_pose
from front_pose import solve_arm
results={}
for w in ['m4','akm']:
 bpy.ops.wm.open_mainfile(filepath=str(source_dir(w,'canted')/(prefix(w,'canted')+'idle.blend')));r=bpy.data.objects['SK_M4_Infima'];bpy.context.scene.frame_set(0)
 old={b.name:b.matrix.copy() for b in r.pose.bones};rest={b.name:b.matrix_local.copy() for b in r.data.bones};G=old['WPN_root']@Matrix(grip_fit(w,'canted')['grip_in_root']);B=G@Matrix(grip_fit('m4','canted')['body_in_grip'])
 base=read(DONOR/'Opening/0.8/aligned_fit.json');H=B@Matrix.Translation((0,0,.008))@Matrix(base['grip_in_root']).inverted()@Matrix(base['hand_in_root']);center=Vector((0,0,-.052))
 front_pose.RP={n:m.copy() for n,m in old.items()}
 rows=[]
 for angle in range(-150,151,15):
  target=B@Matrix.Translation(center)@Matrix.Rotation(math.radians(angle),4,'Z')@Matrix.Translation(-center)@B.inverted()@H
  p={n:m.copy() for n,m in old.items()};metric=solve_arm(p,rest,target,G)
  metric.update({'clock_deg':angle,'old_hand_angle_deg':math.degrees(old['hand_l'].to_quaternion().rotation_difference(target.to_quaternion()).angle),'old_hand_distance_m':(old['hand_l'].translation-target.translation).length,'shoulder_shift_m':Vector(metric['shoulder_delta_m']).length})
  rows.append(metric)
 results[w]=rows
 pivot=B@center
 for blend in [0,.25,.5,.75,1]:
  q=H.to_quaternion().slerp(old['hand_l'].to_quaternion(),blend);dq=q@H.to_quaternion().inverted()
  target=Matrix.LocRotScale(pivot+dq@(H.translation-pivot),q,H.to_scale())
  metric=solve_arm({n:m.copy() for n,m in old.items()},rest,target,G)
  print('REFERENCE_BLEND',w,blend,metric,flush=True)
 print('BASELINE_ARM',w,solve_arm({n:m.copy() for n,m in old.items()},rest,old['hand_l'],G),flush=True)
(O/'canted_clock_audit.json').write_text(json.dumps(results,indent=2));print('CLOCK_CANDIDATES',json.dumps(results),flush=True)
