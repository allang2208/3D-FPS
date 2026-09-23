import bpy, json
from pathlib import Path
O=Path(__file__).parent; S=O.parent/'SVDAttachments20260923'
bpy.ops.wm.open_mainfile(filepath=str(S/'SVD_Modular_Editable.blend'))
r=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE')
a=bpy.data.actions['A_SVD_idle'];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0]
bpy.context.scene.frame_set(0);bpy.context.view_layer.update()
W=r.pose.bones['WPN_root'].matrix
data={'rig':r.name,'rig_matrix':[list(x) for x in r.matrix_world], 'actions':{a.name:list(a.frame_range) for a in bpy.data.actions if a.name.startswith('A_SVD')},'objects':[], 'bones':{n:list((W.inverted()@r.pose.bones[n].matrix).translation) for n in ['hand_l','hand_r','index_03_l','middle_03_l','WPN_SOCKET_Magazine','WPN_bolt']}}
for o in bpy.context.scene.objects:
 if o.type!='MESH':continue
 data['objects'].append({'name':o.name,'vertices':len(o.data.vertices),'matrix':[list(x) for x in o.matrix_world],'materials':[m.name if m else None for m in o.data.materials], 'groups':[g.name for g in o.vertex_groups]})
(O/'probe.json').write_text(json.dumps(data,indent=2))
print('SVD_AUDIT_PROBE',json.dumps({k:v for k,v in data.items() if k!='objects'}),flush=True)
