"""Fit the complete support arm to a rigid, surface-aligned grip."""
import bpy,json,math
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion
O=Path(__file__).parent;R=O.parent
bpy.ops.wm.open_mainfile(filepath=str(R/'HandReload10/PKM_ReloadHands_Editable.blend'))
s=bpy.context.scene;r=bpy.data.objects['PKM_Manny_Rig'];a=bpy.data.actions['PKM_Game_idle'];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0];s.frame_set(0);bpy.context.view_layer.update()
rest={b.name:b.matrix_local.copy() for b in r.data.bones};base={b.name:b.matrix.copy() for b in r.pose.bones};parent={b.name:b.parent.name if b.parent else None for b in r.data.bones}
fit=Matrix(json.loads((R/'Animation03/animation_manifest.json').read_text())['fit_matrix']);W=base['WPN_root']@fit
H0=W.inverted()@base['hand_l'];S0=W.inverted()@base['upperarm_l'].translation;E0=W.inverted()@base['lowerarm_l'].translation
Raxis=(rest['hand_l'].translation-rest['lowerarm_l'].translation).normalized();hand_axis=rest['hand_l'].to_3x3().inverted()@Raxis
l1=(base['lowerarm_l'].translation-base['upperarm_l'].translation).length;l2=(base['hand_l'].translation-base['lowerarm_l'].translation).length
def around(p,m):return Matrix.Translation(p)@m@Matrix.Translation(-Vector(p))
def arm_geometry(S,H):
 P=H.translation;v=P-S;d=v.length
 if not abs(l1-l2)+.005<d<l1+l2-.008:return None
 n=v/d;along=(l1*l1-l2*l2+d*d)/(2*d);height=math.sqrt(max(0,l1*l1-along*along));C=S+n*along
 ideal=P-(H.to_3x3()@hand_axis).normalized()*l2;pole=ideal-C;pole-=n*pole.dot(n)
 if pole.length<1e-5:return None
 E=C+pole.normalized()*height
 bend=math.degrees((P-E).angle(H.to_3x3()@hand_axis));elbow=math.degrees((E-S).angle(P-E))
 return E,bend,elbow
# The contact stays on the narrow support ahead of the receiver, clear of the
# box and carry handle. Compare small whole-grip changes and shoulder offsets.
best=None;fixed=arm_geometry(S0,H0)
for forward_mm in [0,5,10]:
 for down_mm in [0,3,6]:
  for roll in [-10,-5,0,5,10]:
   D=Matrix.Translation((0,-forward_mm/1000,-down_mm/1000))@around((0,-.085,.008),Matrix.Rotation(math.radians(roll),4,'Y'))
   H=D@H0
   for x in [-.02,-.01,0,.01]:
    for y in [-.065,-.05,-.035,-.02,0]:
     for z in [-.04,-.025,-.01,0]:
      shift=Vector((x,y,z));S=S0+shift;g=arm_geometry(S,H)
      if not g:continue
      E,bend,elbow=g
      # Retain the support elbow below/outside the weapon and avoid an
      # extended arm or an artificial shoulder shift to force zero bend.
      if E.x<.10 or E.z>-.055:continue
      loss=max(0,bend-12)**2+.012*shift.length_squared*1e6+.11*roll*roll+.2*(forward_mm**2+down_mm**2)+.05*max(0,35-elbow)**2
      if best is None or loss<best[0]:best=(loss,D,H,S,E,bend,elbow,shift,forward_mm,down_mm,roll)
loss,D,H,S,E,bend,elbow,shift,front,down,roll=best
report={'baseline_bend_deg':41.680836674,'fixed_shoulder_best_bend_deg':fixed[1],
 'fit_bend_deg':bend,'elbow_bend_deg':elbow,'shift_gun_m':list(shift),'grip_front_mm':front,'grip_down_mm':down,'grip_roll_deg':roll,
 'hand_gun':[list(v) for v in H],'shoulder_gun':list(S),'elbow_gun':list(E),'grip_delta':[list(v) for v in D]}
(O/'support_fit.json').write_text(json.dumps(report,indent=2));print(json.dumps({k:v for k,v in report.items() if k not in ['hand_gun','grip_delta']}))
