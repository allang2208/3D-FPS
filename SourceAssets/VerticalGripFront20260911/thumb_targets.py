import bpy,json,math,sys
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion
O=Path(__file__).parent;S=O.parent;sys.path.insert(0,str(O));from front_pose import solve_arm,apply
from inspect_pose import render
sys.path.append(str(S/'VerticalGripErgonomic20260911'));from fit_pose import measure
original=json.loads((O/'before_bones.json').read_text())['original'];report={}
def aim_thumb(r,p,rest,G,targets):
 for j,target in enumerate(targets,1):
  n=f'thumb_{j:02}_l';parent=r.data.bones[n].parent.name;lr=rest[parent].inverted()@rest[n];m=p[parent]@lr@Matrix(original[n]['basis'])
  local_axis=(rest[n].inverted()@rest[f'thumb_{j+1:02}_l']).translation if j<3 else (rest['thumb_02_l'].inverted()@rest['thumb_03_l']).translation
  direction=(m.to_3x3()@local_axis).normalized();desired=(G@Vector(target)-m.translation).normalized();q=direction.rotation_difference(desired)@m.to_quaternion();p[n]=Matrix.LocRotScale(m.translation,q,m.to_scale())
 return p
if __name__=='__main__':
 source=S/'VerticalGripErgonomic20260911/vertical'
 for label,targets in [('d',[(-.008,.031,-.009),(.024,.022,-.012),(.045,.0,-.021)]),('e',[(-.008,.034,-.014),(.024,.021,-.021),(.041,-.003,-.030)]),('f',[(-.008,.034,-.003),(.024,.025,-.005),(.045,.001,-.012)])]:
  bpy.ops.wm.open_mainfile(filepath=str(source/'A_M4_Vertical_idle.blend'));r=bpy.data.objects['SK_M4_Infima'];s=bpy.context.scene;s.frame_set(0);fit=json.loads((source/'fit_final.json').read_text());rest={b.name:b.matrix_local.copy() for b in r.data.bones};p={b.name:b.matrix.copy() for b in r.pose.bones};basis={b.name:b.matrix_basis.copy() for b in r.pose.bones};r.animation_data.action=None
  G=p['WPN_root']@Matrix(fit['grip_in_root']);arm=solve_arm(p,rest,p['hand_l'],G)
  aim_thumb(r,p,rest,G,targets);apply(r,p,rest);result=measure(r,G,'VG_');result['arm']=arm;result['targets']=targets;report[label]=result
  print('TARGET',label,result,flush=True);bpy.ops.wm.save_as_mainfile(filepath=str(O/('candidate_'+label+'.blend')));render(r,fit,'candidate_'+label)
 (O/'target_metrics.json').write_text(json.dumps(report,indent=2))
