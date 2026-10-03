"""Measure elbow roll and hand/forearm motion through the requested recovery."""
import bpy, math, json, argparse, sys
from pathlib import Path
from mathutils import Vector,Matrix
p=argparse.ArgumentParser();p.add_argument('--blend',required=True);p.add_argument('--out',required=True)
a=p.parse_args(sys.argv[sys.argv.index('--')+1:]);bpy.ops.wm.open_mainfile(filepath=a.blend)
rig=bpy.data.objects['SK_FireballCasting_Rig'];scene=bpy.context.scene
action=bpy.data.actions['A_Fireball_CastDetached'];rig.animation_data.action=action
if action.slots:rig.animation_data.action_slot=action.slots[0]
rest=rig.data.bones;RU=rest['lowerarm_l'].head_local-rest['upperarm_l'].head_local;RL=rest['hand_l'].head_local-rest['lowerarm_l'].head_local
def frame(x,z):
    x=x.normalized();z=(z-x*z.dot(x)).normalized();return Matrix((x,x.cross(z),z)).transposed()
ref_plane=RU.cross(RL);ref_frame=frame(RL,ref_plane)
ref_hand=rest['hand_l'].head_local
rf=rest['middle_01_l'].head_local-ref_hand
rn=(rest['pinky_01_l'].head_local-ref_hand).cross(rest['index_01_l'].head_local-ref_hand)
across=frame(rf,rn).col[1]
records=[];prev=None
def shortest_angle(q):
    return 2*math.acos(min(1,abs(q.normalized().w)))
for f in range(round(action.frame_range[1])+1):
    scene.frame_set(f);bpy.context.view_layer.update();pose=rig.pose.bones
    A=pose['upperarm_l'].head.copy();E=pose['lowerarm_l'].head.copy();H=pose['hand_l'].head.copy()
    ud=(E-A).normalized();ld=(H-E).normalized();plane=ud.cross(ld)
    neutral=frame(ld,plane)@ref_frame.inverted()@rest['lowerarm_l'].matrix_local.to_3x3()
    lower=pose['lowerarm_l'].matrix.to_quaternion();hand=pose['hand_l'].matrix.to_quaternion()
    neutral_side=neutral.to_quaternion()@rest['lowerarm_l'].matrix_local.to_quaternion().inverted()@across
    lower_side=lower@rest['lowerarm_l'].matrix_local.to_quaternion().inverted()@across
    n=(neutral_side-ld*neutral_side.dot(ld)).normalized();v=(lower_side-ld*lower_side.dot(ld)).normalized()
    upper=pose['upperarm_l'].matrix.to_quaternion()
    upper_deform=upper@rest['upperarm_l'].matrix_local.to_quaternion().inverted()
    upper_side=upper_deform@across
    target_side=(hand@rest['hand_l'].matrix_local.to_quaternion().inverted())@across
    un=(upper_side-ud*upper_side.dot(ud)).normalized();uv=(target_side-ud*target_side.dot(ud)).normalized()
    carried=(upper_deform@RL).normalized().rotation_difference(ld)@upper_side
    carried=(carried-ld*carried.dot(ld)).normalized()
    fingers=[pose[n].matrix.to_quaternion() for n in ['index_01_l','middle_01_l','ring_01_l','pinky_01_l']]
    rec={'t':f/300,'elbow_roll_deg':math.degrees(math.atan2(ld.dot(n.cross(v)),n.dot(v))),
         'upper_towards_palm_deg':math.degrees(math.atan2(ud.dot(un.cross(uv)),un.dot(uv))),
         'intersegment_roll_deg':math.degrees(math.atan2(ld.dot(carried.cross(v)),carried.dot(v))),
         'wrist_cm':list(H*100),'bone_length_error':max(abs((E-A).length/RU.length-1),abs((H-E).length/RL.length-1)),
         'finger_local_deg':[math.degrees((pose['hand_l'].matrix.to_quaternion().inverted()@q).angle) for q in fingers]}
    if prev:
        rec['wrist_cm_s']=(H-prev[0]).length*30000
        rec['forearm_deg_s']=math.degrees(shortest_angle(lower.rotation_difference(prev[1])))*300
        rec['hand_deg_s']=math.degrees(shortest_angle(hand.rotation_difference(prev[2])))*300
    records.append(rec);prev=(H,lower,hand)
out=Path(a.out);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(records),encoding='utf-8')
recover=[r for r in records if r['t']>=.9 and 'wrist_cm_s' in r]
print(json.dumps({'hold':records[225], 'recover_peak':{k:max(recover,key=lambda r:r[k])['t'] for k in ['wrist_cm_s','forearm_deg_s','hand_deg_s']},
    'recover_values':{k:max(r[k] for r in recover) for k in ['wrist_cm_s','forearm_deg_s','hand_deg_s']}}))
