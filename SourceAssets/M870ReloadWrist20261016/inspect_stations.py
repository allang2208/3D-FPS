import bpy,json,math
from pathlib import Path
O=Path(__file__).parent
bpy.ops.wm.open_mainfile(filepath=str(O/'M870_ReloadWrist_Editable.blend'),use_scripts=False)
r=bpy.data.objects['SK_Super90'];s=bpy.context.scene;rest={b.name:b.matrix_local.copy() for b in r.data.bones}
d=json.loads((O/'authoring.json').read_text());e=d['clips']['reload_continuous'];a=bpy.data.actions[e['action']];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0]
rows=[];chain=['upperarm_r','lowerarm_r','lowerarm_aux_r','lowerarm_twist_02_r','lowerarm_twist_01_r','hand_r']
for f in range(400):
 s.frame_set(f);p={n:r.pose.bones[n].matrix.copy() for n in chain};ds={n:(p[n]@rest[n].inverted()).to_quaternion() for n in chain}
 angles=[math.degrees(min((ds[n].rotation_difference(ds[m])).angle,2*math.pi-(ds[n].rotation_difference(ds[m])).angle)) for n,m in zip(chain,chain[1:])]
 rows.append({'frame':f,'angles':angles,'elbow_step_mm':(p['lowerarm_r'].translation-prev['lowerarm_r'].translation).length*1000 if f else 0,'hand_step_mm':(p['hand_r'].translation-prev['hand_r'].translation).length*1000 if f else 0})
 prev=p
print('LARGEST_STEPS',sorted(rows,key=lambda x:-x['elbow_step_mm'])[:5],flush=True)
print('STATIONS', [row for row in rows if row['frame'] in (18,24,30,40,44,54,60,74,94,344,390)],flush=True)
(O/'station_diagnosis.json').write_text(json.dumps(rows,indent=2))
