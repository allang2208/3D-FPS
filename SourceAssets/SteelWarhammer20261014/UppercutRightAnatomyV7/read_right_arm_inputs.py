"""Read the rejected uppercut's native right elbow/skin frames for authoring."""
import bpy,json,math
from pathlib import Path
from mathutils import Matrix,Vector
P=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(P.parent/'UppercutTiltClearanceV6/Warhammer_Uppercut_TiltClearance_Editable.blend'))
r=bpy.data.objects['SK_RusticPickaxe_Rig'];s=bpy.context.scene
rest={b.name:b.matrix_local.copy() for b in r.data.bones}
names=['clavicle_r','upperarm_r','upperarm_twist_01_r','upperarm_twist_02_r','lowerarm_r','lowerarm_twist_02_r','lowerarm_twist_01_r','hand_r']
u0=rest['lowerarm_r'].translation-rest['upperarm_r'].translation
f0=rest['hand_r'].translation-rest['lowerarm_r'].translation
plane0=u0.cross(f0).normalized()
def axial(q,axis):
    a=2*math.atan2(Vector((q.x,q.y,q.z)).dot(axis),q.w)
    return math.degrees((a+math.pi)%(2*math.pi)-math.pi)
rows=[]
for t in [0,.4,.8,1.,1.025,1.05,1.065,1.075,1.085,1.10,1.125,1.2,1.3,1.4,1.5,1.6,1.75,1.9,2.05]:
    f=t*240;s.frame_set(int(f),subframe=f-int(f));pose={b.name:b.matrix.copy() for b in r.pose.bones}
    u=pose['lowerarm_r'].translation-pose['upperarm_r'].translation
    fore=pose['hand_r'].translation-pose['lowerarm_r'].translation
    plane=u.cross(fore).normalized()
    deform={n:pose[n].to_quaternion()@rest[n].to_quaternion().inverted() for n in names}
    reference=deform['upperarm_twist_02_r'];hinge=(reference@f0).rotation_difference(fore)@reference
    row={'t':t,'joints':{n:list(pose[n].translation) for n in ('upperarm_r','lowerarm_r','hand_r')},
         'neutral_wrist_elbow_m':list(pose['hand_r'].translation-(deform['hand_r']@f0)),
         'wrist_axis_bend':math.degrees(fore.angle(deform['hand_r']@f0)),
         'elbow_flex':math.degrees(u.angle(fore)),
         'hinge_alignment':{n:math.degrees(plane.angle(deform[n]@plane0)) for n in ('upperarm_r','upperarm_twist_01_r','upperarm_twist_02_r')},
         'forearm_roll_from_hinge':{n:axial(deform[n]@hinge.inverted(),fore.normalized()) for n in ('lowerarm_r','lowerarm_twist_02_r','lowerarm_twist_01_r','hand_r')},
         'bones':{n:[list(v) for v in pose[n]] for n in names}}
    rows.append(row)
    print(json.dumps({k:v for k,v in row.items() if k!='bones'}))
(P/'right_arm_inputs.json').write_text(json.dumps({'rest':{n:[list(v) for v in rest[n]] for n in names},'samples':rows},indent=2),encoding='utf-8')
