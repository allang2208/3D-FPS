import bpy,json,math
from pathlib import Path
from mathutils import Vector
O=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(O.parent/'M24MotionMagazine20261027/M24_MotionMagazine_Editable.blend'),use_scripts=False)
r=bpy.data.objects['M24_V9_Rig'];s=bpy.context.scene
a=bpy.data.actions['A_M24_aim'];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0];s.frame_set(0);bpy.context.view_layer.update()
rest={b.name:b.matrix_local.copy() for b in r.data.bones};pose={b.name:b.matrix.copy() for b in r.pose.bones}
out={'rest':{n:[list(v) for v in m] for n,m in rest.items()},'pose':{n:[list(v) for v in m] for n,m in pose.items()},'parents':{b.name:b.parent.name if b.parent else None for b in r.data.bones},'fingers':{}}
for b in r.data.bones:
 if not b.name.endswith('_l') or not any(k in b.name for k in ('thumb','index','middle','ring','pinky')):continue
 local=pose[b.parent.name].inverted()@pose[b.name];lr=rest[b.parent.name].inverted()@rest[b.name]
 q=(lr.inverted()@local).to_quaternion();axis,angle=q.to_axis_angle()
 out['fingers'][b.name]={'rest':list(rest[b.name].translation),'pose':list(pose[b.name].translation),'angle':math.degrees(angle),'axis':list(axis),'length':b.length}
base=bpy.data.objects['M24_base'];me=base.data;me.calc_loop_triangles()
out['gun']={'vertices':[list(v.co) for v in me.vertices],'triangles':[list(t.vertices) for t in me.loop_triangles]}
(O/'inputs.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
for n,row in out['fingers'].items():print(n,'rotation',round(row['angle'],1),'axis',[round(v,3) for v in row['axis']],'position',[round(v,4) for v in row['pose']],flush=True)
v=[p.co for p in me.vertices if .28<p.co.y<.43]
print('FOREND_SECTION',[[min(p[i] for p in v),max(p[i] for p in v)] for i in range(3)],flush=True)
