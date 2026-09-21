import bpy,json,numpy as np
from pathlib import Path
O=Path(__file__).parent
bpy.ops.wm.open_mainfile(filepath=str(O.parent/'Refinement04/A762_StockJoint_Editable.blend'))
r=bpy.data.objects['SK_M4_Infima'];r.animation_data.action=bpy.data.actions['A_A762_idle'];r.animation_data.action_slot=r.animation_data.action.slots[0]
r.data.pose_position='POSE';bpy.context.scene.frame_set(0);bpy.context.view_layer.update()
root=r.pose.bones['WPN_root'].matrix;out={}
for col in ['A762_REFINED_GEOMETRY','A762_RECONSTRUCTED_02','A762_CLOSED_SURFACES_03','A762_STOCK_JOINT_04']:
 for ob in bpy.data.collections[col].objects:
  if ob.type!='MESH':continue
  bone=next((g.name for g in ob.vertex_groups if g.name.startswith('WPN_')),None)
  if not bone:continue
  xf=root.inverted()@r.pose.bones[bone].matrix@r.data.bones[bone].matrix_local.inverted()
  v=np.array([tuple(xf@p.co) for p in ob.data.vertices])
  if 'Sight' in ob.name or ob.name in ['A762_Receiver','A762_FactoryRearGrip']:
   out[ob.name]={'min':v.min(0).tolist(),'max':v.max(0).tolist(),'fold':bool(ob.get('independent_folding_head',False)),'materials':[m.name for m in ob.data.materials]}
out['mag_idle_from_root']=[list(row) for row in r.pose.bones['WPN_SOCKET_Magazine'].matrix.inverted()@root]
(O/'authoring_frames.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
src=json.loads((O/'sources.json').read_text())
out={}
for key in ['vertical','drum','skeleton','phantom_reargrip','suppressor','tactical_suppressor']:
 bpy.ops.wm.read_factory_settings(use_empty=True)
 bpy.ops.import_scene.fbx(filepath=src['meshes'][key]['source'][0])
 out[key]=[]
 for ob in bpy.context.scene.objects:
  if ob.type!='MESH':continue
  v=np.array([tuple(ob.matrix_world@p.co) for p in ob.data.vertices])
  out[key].append({'name':ob.name,'min':v.min(0).tolist(),'max':v.max(0).tolist(),'materials':[m.name for m in ob.data.materials]})
(O/'donor_frames.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
print('A762_AUTHORING_FRAMES_READY',flush=True)
