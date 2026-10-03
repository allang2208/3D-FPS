"""Capture the existing support and native fore-end grip in weapon space."""
import bpy,json
from pathlib import Path
from mathutils import Vector
O=Path(__file__).parent
bpy.ops.wm.open_mainfile(filepath=str(O/'Support_Working.blend'))
r=bpy.data.objects['SK_M4_Infima'];s=bpy.context.scene
data={'rest':{b.name:[list(row) for row in b.matrix_local] for b in r.data.bones},
      'parents':{b.name:b.parent.name if b.parent else None for b in r.data.bones},'poses':{}}
for f in (254,272,320,385,400,450):
    s.frame_set(f);bpy.context.view_layer.update();root=r.pose.bones['WPN_root'].matrix.inverted()
    data['poses'][str(f)]={'hand_in_root':[list(row) for row in root@r.pose.bones['hand_l'].matrix],
      'basis':{b.name:list(b.matrix_basis.to_quaternion()) for b in r.pose.bones if b.name.endswith('_l')},
      'bones_root':{b.name:[list(row) for row in root@b.matrix] for b in r.pose.bones}}
s.frame_set(320);bpy.context.view_layer.update();root=r.pose.bones['WPN_root'].matrix.inverted()
verts=[];faces=[];objects=[]
for ob in s.objects:
    if ob.type!='MESH' or ob.hide_render or not ob.name.startswith('A762_'):continue
    if not any(word in ob.name for word in ('Handguard','Receiver','Rail_ContinuousSeat')):continue
    dg=bpy.context.evaluated_depsgraph_get();ev=ob.evaluated_get(dg);me=ev.to_mesh()
    offset=len(verts);xf=root@ob.matrix_world
    verts.extend([list(xf@v.co) for v in me.vertices]);faces.extend([[offset+i for i in p.vertices] for p in me.polygons]);objects.append(ob.name)
    ev.to_mesh_clear()
data['body']={'vertices':verts,'faces':faces,'objects':objects}
(O/'support_input.json').write_text(json.dumps(data),encoding='utf-8')
print('SUPPORT_INPUT',len(verts),len(faces),objects,flush=True)
