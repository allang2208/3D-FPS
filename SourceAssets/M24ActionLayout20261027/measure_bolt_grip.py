import bpy,json
from pathlib import Path
from mathutils import Vector
O=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(O.parent/'M24Hold20261027/M24_Hold_Editable.blend'),use_scripts=False)
r=bpy.data.objects['M24_V9_Rig'];s=bpy.context.scene
a=bpy.data.actions['A_M24_fire'];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0]
s.frame_set(28);bpy.context.view_layer.update();g=r.pose.bones['WPN_root'].matrix.inverted()
out={'bones':{},'meshes':{}}
for b in r.pose.bones:
    if b.name.startswith(('hand_r','index_','middle_','thumb_','ring_','pinky_','WPN_Bolt')) and (b.name.endswith('_r') or b.name.startswith('WPN_')):
        out['bones'][b.name]={'head':list(g@b.head),'tail':list(g@b.tail)}
dg=bpy.context.evaluated_depsgraph_get()
for ob in s.objects:
    if ob.type!='MESH' or not any(w in ob.name.lower() for w in ('bolt','scope')):continue
    e=ob.evaluated_get(dg);m=e.to_mesh();v=[g@r.matrix_world.inverted()@e.matrix_world@p.co for p in m.vertices]
    out['meshes'][ob.name]={'min':[min(p[i] for p in v) for i in range(3)],'max':[max(p[i] for p in v) for i in range(3)],'groups':list(ob.vertex_groups.keys())}
    if ob.name=='M24_bolt':
        tip=[p for p in v if p.x>.04]
        out['knob']={'min':[min(p[i] for p in tip) for i in range(3)],'max':[max(p[i] for p in tip) for i in range(3)]}
    e.to_mesh_clear()
(O/'bolt_grip_measure.json').write_text(json.dumps(out,indent=2))
print('M24_BOLT_GRIP_MEASURED',flush=True)
