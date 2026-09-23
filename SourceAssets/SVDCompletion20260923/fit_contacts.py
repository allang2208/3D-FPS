import bpy,json
from pathlib import Path
from mathutils import Vector
O=Path('D:/FPS3D/FPSGAME/SourceAssets/SVDCompletion20260923');S=O.parent;out={}
def sample(r,a,f):
 r.animation_data.action=a;r.animation_data.action_slot=a.slots[0];bpy.context.scene.frame_set(f);bpy.context.view_layer.update();return {b.name:b.matrix.copy() for b in r.pose.bones}
def center(vs):return Vector(((min(v[i] for v in vs)+max(v[i] for v in vs))*.5 for i in range(3)))
bpy.ops.wm.open_mainfile(filepath=str(S/'M4TacticalToss20260910/M4_Hand_MAT_Editable.blend'));r=bpy.data.objects['SK_M4_Infima'];a=bpy.data.actions['M4_HK416_reload'];p=sample(r,a,76)
mag=next(o for o in bpy.context.scene.objects if o.type=='MESH' and 'Magazine' in o.name and o.name.endswith('_Export'))
e=mag.evaluated_get(bpy.context.evaluated_depsgraph_get());inv=(r.matrix_world@p['WPN_SOCKET_Magazine']).inverted();vs=[inv@e.matrix_world@v.co for v in e.data.vertices]
G=p['WPN_SOCKET_Magazine'].inverted()@p['hand_l'];doncenter=center(vs);out['finger_basis']={b.name:list(b.matrix_basis.to_quaternion()) for b in r.pose.bones if b.name.endswith('_l') and b.name.startswith(('thumb','index','middle','ring','pinky'))}
bpy.ops.wm.open_mainfile(filepath=str(O/'SVD_Complete_Editable.blend'));r=bpy.data.objects['SK_M4_Infima'];p=sample(r,bpy.data.actions['A_SVD_idle'],0);mag=bpy.data.objects['SM_SVD_Magazine'];e=mag.evaluated_get(bpy.context.evaluated_depsgraph_get());inv=(r.matrix_world@p['WPN_SOCKET_Magazine']).inverted();vs=[inv@e.matrix_world@v.co for v in e.data.vertices];newcenter=center(vs);G.translation+=newcenter-doncenter;out['hand_in_mag']=[list(x) for x in G];out['center_delta']=list(newcenter-doncenter)
p=sample(r,bpy.data.actions['A_SVD_reload_empty'],310);arms=bpy.data.objects['SK_Manny_Arms_Export'];e=arms.evaluated_get(bpy.context.evaluated_depsgraph_get());inv=(r.matrix_world@p['WPN_root']).inverted();knob=Vector(json.loads((O/'authoring.json').read_text())['charging_handle_root'])
out['charge']={}
for part in ['index','middle','thumb']:
 groups={g.index for g in arms.vertex_groups if g.name.startswith(part+'_') and g.name.endswith('_r')};ids=[v.index for v in arms.data.vertices if any(g.group in groups and g.weight>.3 for g in v.groups)];points=[inv@e.matrix_world@e.data.vertices[i].co for i in ids];nearest=min(points,key=lambda v:(v-knob).length);out['charge'][part]={'nearest':list(nearest),'distance_mm':(nearest-knob).length*1000,'knob':list(knob)}
(O/'contact_fit.json').write_text(json.dumps(out,indent=2));print('CONTACT_FIT',out['center_delta'],out['charge'])
