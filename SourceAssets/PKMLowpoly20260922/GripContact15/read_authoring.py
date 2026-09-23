"""Read the existing authoring contact frames for the requested correction."""
import bpy,json,math
from pathlib import Path
from mathutils import Vector,Matrix
O=Path(__file__).parent;A=O.parent/'Accessories14'
report={'arms':{},'reargrips':{}}
def arr(m):return [list(v) for v in m]
def region(o):
 p=[o.matrix_world@v.co for v in o.data.vertices]
 return {'name':o.name,'materials':[m.name for m in o.data.materials], 'min':[min(v[i] for v in p) for i in range(3)],'max':[max(v[i] for v in p) for i in range(3)],'count':len(p)}
for family in ['vertical','canted','prism','angled']:
 bpy.ops.wm.open_mainfile(filepath=str(A/f'PKM_{family}_Editable.blend'))
 r=bpy.data.objects['PKM_Manny_Rig'];r.animation_data.action=bpy.data.actions[f'A_PKM_{family}_idle'];r.animation_data.action_slot=r.animation_data.action.slots[0];bpy.context.scene.frame_set(0);bpy.context.view_layer.update()
 names=['clavicle_l','upperarm_l','upperarm_twist_01_l','upperarm_twist_02_l','lowerarm_l','lowerarm_twist_01_l','lowerarm_twist_02_l','hand_l','hand_r','WPN_root']
 bones={n:{'pose':arr(r.pose.bones[n].matrix),'rest':arr(r.data.bones[n].matrix_local),'parent':r.data.bones[n].parent.name if r.data.bones[n].parent else None} for n in names}
 low=r.pose.bones['lowerarm_l'];h=r.pose.bones['hand_l'];rest=r.data.bones
 axis=(h.head-low.head).normalized();raxis=(rest['hand_l'].head_local-rest['lowerarm_l'].head_local).normalized();dh=h.matrix.to_quaternion()@rest['hand_l'].matrix_local.to_quaternion().inverted();df=low.matrix.to_quaternion()@rest['lowerarm_l'].matrix_local.to_quaternion().inverted()
 dq=dh@df.inverted();v=Vector((dq.x,dq.y,dq.z));proj=v.dot(axis)
 report['arms'][family]={'bones':bones,'bend_deg':math.degrees(axis.angle(dh@raxis)),'wrist_relative_deg':math.degrees(dq.angle),'twist_deg':math.degrees(2*math.atan2(proj,dq.w))}
 if family=='vertical':
  fit=Matrix(json.loads((O.parent/'Animation03/animation_manifest.json').read_text())['fit_matrix']);G=r.data.bones['WPN_root'].matrix_local@fit
  report['gun_frame']=arr(G);report['factory_grip']=[]
  for i in [45,46]:
   ob=bpy.data.objects[f'PKM_Part_{i:03}'];row=region(ob);row['vertices_gun']=[list(G.inverted()@ob.matrix_world@v.co) for v in ob.data.vertices];report['factory_grip'].append(row)
  report['arm_meshes']=[]
  for ob in bpy.context.scene.objects:
   if ob.type=='MESH' and ob.vertex_groups.get('hand_l'):
    weights={n:0. for n in names}
    for v in ob.data.vertices:
     for g in v.groups:
      n=ob.vertex_groups[g.group].name
      if n in weights:weights[n]+=g.weight
    report['arm_meshes'].append({'name':ob.name,'weights':weights})
for key in ['phantom_reargrip','balanced_reargrip','stable_antislip_reargrip']:
 bpy.ops.wm.open_mainfile(filepath=str(A/f'SM_PKM_{key}.blend'))
 report['reargrips'][key]=[]
 for ob in bpy.context.scene.objects:
  if ob.type!='MESH':continue
  row=region(ob);row['vertices']=[list(ob.matrix_world@v.co) for v in ob.data.vertices]
  row['material_vertices']={str(i):list({v for p in ob.data.polygons if p.material_index==i for v in p.vertices}) for i in range(len(ob.data.materials))}
  report['reargrips'][key].append(row)
(O/'source_frames.json').write_text(json.dumps(report,indent=2))
print('PKM15_SOURCE_FRAMES_READY')
