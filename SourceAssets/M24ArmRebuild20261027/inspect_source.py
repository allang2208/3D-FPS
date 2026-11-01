import bpy,json,math,numpy as np
from pathlib import Path
from mathutils import Matrix,Vector
O=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(O.parent/'M24MotionPolish20261027/M24_MotionPolish_Editable.blend'),use_scripts=False)
r=bpy.data.objects['M24_V9_Rig'];s=bpy.context.scene
rest={b.name:b.matrix_local.copy() for b in r.data.bones};parents={b.name:b.parent.name if b.parent else None for b in r.data.bones}
def metric(row,side):
 u,l,h=[x+'_'+side for x in ('upperarm','lowerarm','hand')]
 U=row[l].translation-row[u].translation;L=row[h].translation-row[l].translation
 RU=rest[l].translation-rest[u].translation;RL=rest[h].translation-rest[l].translation
 expected=row[u].to_quaternion()@rest[u].to_quaternion().inverted()@RU.cross(RL).normalized()
 axis=rest[l].to_quaternion().inverted()@RL.normalized()
 rel=(row[l].to_quaternion().inverted()@row[h].to_quaternion())@(rest[l].to_quaternion().inverted()@rest[h].to_quaternion()).inverted()
 if rel.w<0:rel.negate()
 twist=2*math.atan2(Vector((rel.x,rel.y,rel.z)).dot(axis),rel.w)
 swing=math.degrees(math.acos(max(-1,min(1,2*(rel.w*rel.w+Vector((rel.x,rel.y,rel.z)).dot(axis)**2)-1))))
 return {'hinge':math.degrees(expected.angle(U.cross(L))),'bend':math.degrees(U.angle(L)),'roll':math.degrees(twist),'wrist':swing}
out={'rest':{n:[list(x) for x in m] for n,m in rest.items()},'parents':parents,'clips':{}}
for a in bpy.data.actions:
 if not a.name.startswith('A_M24_'):continue
 role=a.name[6:];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0];rows=[];poses=[]
 for f in range(round(a.frame_range[1])+1):
  s.frame_set(f);bpy.context.view_layer.update();row={b.name:b.matrix.copy() for b in r.pose.bones}
  rows.append({side:metric(row,side) for side in ('l','r')});poses.append({n:[list(x) for x in m] for n,m in row.items()})
 out['clips'][role]={'metrics':rows,'poses':poses}
 print(role,{side:{k:round(max(v[side][k] for v in rows),1) for k in rows[0][side]} for side in ('l','r')},flush=True)
(O/'source_before.json').write_text(json.dumps(out),encoding='utf-8')
for side in ('l','r'):
 print('BIND',side,[(n,parents[n],[round(x,4) for x in rest[n].translation]) for n in rest if n.endswith('_'+side) and any(x in n for x in ('upperarm','lowerarm','hand'))],flush=True)
