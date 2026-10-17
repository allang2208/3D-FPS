import bpy,json,math,gzip,numpy as np
from pathlib import Path
from mathutils import Vector,Matrix
O=Path(__file__).parent;S=O.parent
bpy.ops.wm.open_mainfile(filepath=str(S/'M870Super90Sprint20261016/M870_Super90Sprint_Editable.blend'),use_scripts=False)
r=bpy.data.objects['SK_Super90'];s=bpy.context.scene
rest={b.name:b.matrix_local.copy() for b in r.data.bones};parents={b.name:b.parent.name if b.parent else None for b in r.data.bones}
local={n:rest[parents[n]].inverted()@m if parents[n] else m for n,m in rest.items()}
rf=rest['hand_r'].translation-rest['lowerarm_r'].translation
with gzip.open(O/'native_arms.json.gz','rt',encoding='utf-8') as f:skin=json.load(f)
sample_frames=[0,9,18,24,30,40,44,48,54,60,74,84,94,104,144,194,244,294,344,350,359,360,366,372,390,399,410,424]
R={'clips':{},'stations':{n:(rest[n].translation-rest['lowerarm_r'].translation).dot(rf)/rf.length_squared for n in ('lowerarm_r','lowerarm_aux_r','lowerarm_twist_02_r','lowerarm_twist_01_r')},'rest':{n:[list(v) for v in m] for n,m in rest.items()}}
auth=json.loads((S/'M870ReloadContact20261016/authoring.json').read_text())
for role,entry in auth['clips'].items():
 a=bpy.data.actions[entry['action']];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0];rows=[]
 for frame in sample_frames:
  if frame>entry['duration']*60+.1:continue
  s.frame_set(frame);row={b.name:b.matrix.copy() for b in r.pose.bones};hd=row['hand_r']@rest['hand_r'].inverted();fore=row['hand_r'].translation-row['lowerarm_r'].translation
  bd=math.degrees((hd.to_quaternion()@rf).angle(fore))
  errors=[]
  for n in rest:
   if not n.endswith('_r') or not parents[n]:continue
   lm=row[parents[n]].inverted()@row[n]
   errors.append(((lm.translation-local[n].translation).length*1000,n))
  rotations={n:math.degrees((row[n]@rest[n].inverted()).to_quaternion().rotation_difference(hd.to_quaternion()).angle) for n in ('lowerarm_r','lowerarm_aux_r','lowerarm_twist_02_r','lowerarm_twist_01_r')}
  rows.append({'frame':frame,'wrist_bend_degrees':bd,'hand_vs_forearm_degrees':rotations,'local_translation_errors_mm':sorted(errors,reverse=True)[:5]})
 R['clips'][role]=rows
idle_entry=json.loads((S/'M870AKMArmSupport20261016/authoring.json').read_text())['clips']['idle']
a=bpy.data.actions[idle_entry['action']];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0];s.frame_set(0)
ip={b.name:b.matrix.copy() for b in r.pose.bones};R['idle']={n:[list(v) for v in m] for n,m in ip.items()}
R['idle_wrist_bend_degrees']=math.degrees(((ip['hand_r']@rest['hand_r'].inverted()).to_quaternion()@rf).angle(ip['hand_r'].translation-ip['lowerarm_r'].translation))
(O/'before_diagnosis.json').write_text(json.dumps(R,indent=2))
print('M870_IDLE_WRIST',R['idle_wrist_bend_degrees'],flush=True)
for role,rows in R['clips'].items():print('M870_WRIST_DIAGNOSIS',role,[(a['frame'],round(a['wrist_bend_degrees'],1),a['local_translation_errors_mm'][0]) for a in rows[:10]],flush=True)
