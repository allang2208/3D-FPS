"""Production inputs: accepted grouped grasps and actual target skin/interfaces."""
import bpy,json
from pathlib import Path
from mathutils import Vector,Matrix
O=Path(__file__).parent;S=O.parent
def sample(r,name,frame):
 a=bpy.data.actions[name];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0];bpy.context.scene.frame_set(frame);bpy.context.view_layer.update();return {b.name:b.matrix.copy() for b in r.pose.bones}
def mesh(o,space):
 ev=o.evaluated_get(bpy.context.evaluated_depsgraph_get());m=ev.to_mesh();v=[list(space@o.matrix_world@x.co) for x in m.vertices];f=[list(p.vertices) for p in m.polygons];ev.to_mesh_clear();return {'vertices':v,'faces':f}
def fingers(r,side):return {b.name:list(b.matrix_basis.to_quaternion()) for b in r.pose.bones if b.name.endswith('_'+side) and b.name.startswith(('thumb','index','middle','ring','pinky'))}
bpy.ops.wm.open_mainfile(filepath=str(S/'M4TacticalToss20260910/M4_Hand_MAT_Editable.blend'));r=bpy.data.objects['SK_M4_Infima'];p=sample(r,'M4_MAT_reload',76)
mag=next(o for o in bpy.context.scene.objects if o.type=='MESH' and 'Magazine' in o.name and o.name.endswith('_Export'))
donor={'name':'M4_MAT_reload','frame':76,'fps':60,'source':str(S/'M4TacticalToss20260910/M4_Hand_MAT_Editable.blend'),'hand_in_mag':[list(x) for x in p['WPN_SOCKET_Magazine'].inverted()@p['hand_l']],'finger_basis':fingers(r,'l'),'magazine':mesh(mag,(r.matrix_world@p['WPN_SOCKET_Magazine']).inverted())}
donor['rest']={b.name:[list(x) for x in b.matrix_local] for b in r.data.bones};donor['pose']={n:[list(x) for x in m] for n,m in p.items()}
bpy.ops.wm.open_mainfile(filepath=str(S/'SVDAttachments20260923/SVD_Modular_Editable.blend'));r=bpy.data.objects['SK_M4_Infima'];p=sample(r,'A_SVD_idle',0);W=r.matrix_world@p['WPN_root'];arms=bpy.data.objects['SK_Manny_Arms_Export'];out={'donor':donor,'targets':{}}
for name in ['Body','Magazine','ChargingHandle']:
 space=(r.matrix_world@p['WPN_SOCKET_Magazine']).inverted() if name=='Magazine' else W.inverted()
 out['targets'][name]=mesh(bpy.data.objects['SM_SVD_'+name],space)
out['idle']={n:[list(x) for x in m] for n,m in p.items()};out['idle_fingers']=fingers(r,'l');out['rest']={b.name:[list(x) for x in b.matrix_local] for b in r.data.bones};out['parents']={b.name:b.parent.name if b.parent else None for b in r.data.bones}
out['skin']={}
for side in ['l','r']:
 names=[b.name for b in r.data.bones if b.name=='hand_'+side or b.name.endswith('_'+side) and b.name.startswith(('thumb','index','middle','ring','pinky'))]
 use=[v.index for v in arms.data.vertices if sum(g.weight for g in v.groups if arms.vertex_groups[g.group].name in names)>.98];lookup={v:i for i,v in enumerate(use)}
 out['skin'][side]={'names':names,'vertices':[list(r.matrix_world.inverted()@arms.matrix_world@arms.data.vertices[i].co) for i in use],'weights':[{arms.vertex_groups[g.group].name:g.weight for g in arms.data.vertices[i].groups if arms.vertex_groups[g.group].name in names} for i in use],'faces':[[lookup[i] for i in f.vertices] for f in arms.data.polygons if all(i in lookup for i in f.vertices)]}
hook=json.loads((S/'A762RightCharge20260922/fitted_contact.json').read_text());refs=json.loads((S/'A762RightCharge20260922/reference_poses.json').read_text());h=Matrix(hook['hand_in_root']);landmark=Vector(json.loads((S/'SVDCompletion20260923/authoring.json').read_text())['charging_handle_root']);h.translation+=landmark-Vector((-.0358,-.1694,.075))
out['hook']={'hand_in_root':[list(x) for x in h],'finger_basis':{n:q for n,q in refs['ASH12']['samples']['140.4']['basis'].items() if n.endswith('_r') and n.startswith(('thumb','index','middle','ring','pinky'))},'landmark':list(landmark)}
(O/'inputs.json').write_text(json.dumps(out));print('SVD_REPAIR_INPUTS',donor['name'],flush=True)
