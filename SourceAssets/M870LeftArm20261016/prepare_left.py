import bpy,json,math
from pathlib import Path
from mathutils import Matrix,Vector
O=Path(__file__).parent;S=O.parent
bpy.ops.wm.open_mainfile(filepath=str(S/'M870TriggerGrip20261016/M870_TriggerGrip_Editable.blend'),use_scripts=False)
r=bpy.data.objects['SK_Super90'];s=bpy.context.scene
rest={b.name:b.matrix_local.copy() for b in r.data.bones};names=list(rest);parents={b.name:b.parent.name if b.parent else None for b in r.data.bones}
vr={n:Matrix(m) for n,m in json.loads((S/'Super90QuickMelee20261008/LeftArmR5/v7_skin_basis.json').read_text())['rest'].items()}
warp={n:Matrix(m) for n,m in json.loads((S/'BenelliM4Super9020261006/authoring.json').read_text())['v7_to_native_warp'].items()}
rf=rest['hand_l'].translation-rest['lowerarm_l'].translation;ru=rest['lowerarm_l'].translation-rest['upperarm_l'].translation
vh=(vr['lowerarm_l'].translation-vr['upperarm_l'].translation).cross(vr['hand_l'].translation-vr['lowerarm_l'].translation).normalized()
uh=(warp['upperarm_l'].to_3x3()@vh).normalized();fh=(warp['lowerarm_l'].to_3x3()@vh).normalized()
auth=json.loads((S/'M870TriggerGrip20261016/authoring.json').read_text());entry=auth['clips']['idle'];a=bpy.data.actions[entry['action']];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0];s.frame_set(0)
row={b.name:b.matrix.copy() for b in r.pose.bones};arm=row['lowerarm_l'].translation-row['upperarm_l'].translation;fore=row['hand_l'].translation-row['lowerarm_l'].translation;hinge=arm.cross(fore).normalized();hd=(row['hand_l']@rest['hand_l'].inverted()).to_quaternion()
data={'upper_hinge_error_deg':math.degrees(((row['upperarm_l']@rest['upperarm_l'].inverted()).to_quaternion()@uh).angle(hinge)),'wrist_axis_bend_deg':math.degrees((hd@rf).angle(fore)),'stations':{},'native_hinge':{'upper':list(uh),'fore':list(fh)},'rest':{n:[list(v) for v in m] for n,m in rest.items()},'idle':{n:[list(v) for v in m] for n,m in row.items()},'parents':parents}
for n in ('lowerarm_l','lowerarm_aux_l','lowerarm_twist_02_l','lowerarm_twist_01_l'):
 dq=(row[n]@rest[n].inverted()).to_quaternion();station=(rest[n].translation-rest['lowerarm_l'].translation).dot(rf)/rf.length_squared
 data['stations'][n]={'station':station,'shaft_error_deg':math.degrees((dq@rf).angle(fore)),'hand_rotation_difference_deg':math.degrees(dq.rotation_difference(hd).angle),'elbow_distance_mm':(row[n].translation-row['lowerarm_l'].translation).length*1000}
(O/'before_diagnosis.json').write_text(json.dumps(data,indent=2),encoding='utf-8')
print('M870_LEFT_DIAGNOSIS',json.dumps({k:v for k,v in data.items() if k not in ('rest','idle','parents')}),flush=True)
