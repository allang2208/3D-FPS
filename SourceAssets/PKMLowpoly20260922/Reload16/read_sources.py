import bpy,json,math
from pathlib import Path
from mathutils import Matrix,Vector
O=Path(__file__).parent;R=O.parent;out={}
def mat(m):return [list(v) for v in m]
def set_action(r,a,f):
 r.animation_data.action=a;r.animation_data.action_slot=a.slots[0];bpy.context.scene.frame_set(int(f),subframe=f%1);bpy.context.view_layer.update()
bpy.ops.wm.open_mainfile(filepath=str(R/'Feed13/PKM_FiringFeed_Editable.blend'))
r=bpy.data.objects['PKM_Manny_Rig'];fit=Matrix(json.loads((R/'Animation03/animation_manifest.json').read_text())['fit_matrix']);B=r.data.bones['WPN_root'].matrix_local@fit
out['pkm']={'rest':{b.name:mat(b.matrix_local) for b in r.data.bones},'parent':{b.name:b.parent.name if b.parent else None for b in r.data.bones},'poses':{},'charge_geometry':[]}
normal=bpy.data.actions['PKM_Reload_Normal_HandReload10_Wrist12'];empty=bpy.data.actions['PKM_Reload_Empty_HandReload10_Wrist12']
for t in [0,.65,1.06,1.2,1.43,1.65,1.9,2.13,2.3,5.9,6.03,6.20,6.42,6.45,6.55,7.16]:
 set_action(r,normal if t<3 else empty,t*60);W=r.pose.bones['WPN_root'].matrix@fit
 p={b.name:mat(b.matrix) for b in r.pose.bones if b.name.endswith(('_l','_r')) or b.name in ['WPN_root','PKM_Charge']}
 bend={}
 for side in ['l','r']:
  H=r.pose.bones['hand_'+side].matrix;F=r.pose.bones['lowerarm_'+side].matrix;rest=r.data.bones
  axis=(H.translation-F.translation).normalized();raxis=(rest['hand_'+side].head_local-rest['lowerarm_'+side].head_local).normalized()
  aligned=H.to_quaternion()@rest['hand_'+side].matrix_local.to_quaternion().inverted()@raxis
  bend[side]=math.degrees(axis.angle(aligned))
 out['pkm']['poses'][str(t)]={'bones':p,'bend_deg':bend,'gun_frame':mat(W)}
for ob in bpy.context.scene.objects:
 if ob.type=='MESH' and ob.get('mechanical_bone')=='PKM_Charge':
  points=[B.inverted()@ob.matrix_world@v.co for v in ob.data.vertices]
  out['pkm']['charge_geometry'].append({'name':ob.name,'source':ob.get('source_name'),'min':[min(p[i] for p in points) for i in range(3)],'max':[max(p[i] for p in points) for i in range(3)],'points':[list(p) for p in points]})
bpy.ops.wm.open_mainfile(filepath=str(R.parent/'AKMIntegration20260910/EquipCharge/AKM_EquipCharge_Editable.blend'))
r=bpy.data.objects['SK_M4_Infima'];a=bpy.data.actions['AKM_EquipCharge'];out['donor']={'file':bpy.data.filepath,'fps':bpy.context.scene.render.fps,'duration':1.7,'rest':{b.name:mat(b.matrix_local) for b in r.data.bones},'poses':{},'geometry':[]}
for f in [0,54,66,75,84,96,112,132,170,204]:
 set_action(r,a,f)
 out['donor']['poses'][str(f)]={b.name:mat(b.matrix) for b in r.pose.bones if b.name.endswith('_r') or b.name in ['WPN_root','WPN_bolt']}
for ob in bpy.context.scene.objects:
 if ob.type!='MESH' or not ob.vertex_groups.get('WPN_bolt'):continue
 gid=ob.vertex_groups['WPN_bolt'].index
 points=[ob.matrix_world@v.co for v in ob.data.vertices if any(g.group==gid and g.weight>.5 for g in v.groups)]
 if points:out['donor']['geometry'].append({'name':ob.name,'min':[min(p[i] for p in points) for i in range(3)],'max':[max(p[i] for p in points) for i in range(3)],'points':[list(p) for p in points]})
(O/'sources.json').write_text(json.dumps(out,indent=2));print('PKM16_SOURCE_READY')
