"""Requested QBZ grip diagnosis: bone contact and actual hand skin invariance."""
import bpy,json,math
from pathlib import Path
P=Path(__file__).parent
manifest=json.loads((P/'authoring.json').read_text());report={}
for profile,item in manifest['weapons']['QBZ191']['profiles'].items():
 bpy.ops.wm.open_mainfile(filepath=item['blend']);rig=bpy.data.objects['SK_M4_Infima'];scene=bpy.context.scene
 rest={b.name:b.matrix_local.copy() for b in rig.data.bones};children=[b.name for b in rig.data.bones['hand_r'].children_recursive]
 ref=(rest['hand_r'].translation-rest['lowerarm_r'].translation).normalized()
 scene.frame_set(0);bpy.context.view_layer.update();idle={b.name:b.matrix.copy() for b in rig.pose.bones}
 grip=idle['WPN_root'].inverted()@idle['hand_r'];locals0={n:idle[rig.data.bones[n].parent.name].inverted()@idle[n] for n in children}
 lengths0=[(idle[a].translation-idle[b].translation).length for a,b in [('lowerarm_r','upperarm_r'),('hand_r','lowerarm_r')]]
 rows=[]
 for step in range(865):
  f=step/8;scene.frame_set(int(f),subframe=f%1);bpy.context.view_layer.update()
  p={b.name:b.matrix.copy() for b in rig.pose.bones};h=p['WPN_root'].inverted()@p['hand_r']
  desired=p['hand_r'].to_quaternion()@rest['hand_r'].to_quaternion().inverted()@ref
  fore=(p['hand_r'].translation-p['lowerarm_r'].translation).normalized()
  localerr=max(max(abs((p[rig.data.bones[n].parent.name].inverted()@p[n])[i][j]-locals0[n][i][j]) for i in range(4) for j in range(4)) for n in children)
  lengths=[(p[a].translation-p[b].translation).length for a,b in [('lowerarm_r','upperarm_r'),('hand_r','lowerarm_r')]]
  rows.append({'frame':f,'grip_shift_mm':1000*(h.translation-grip.translation).length,
   'grip_rotation_matrix_error':max(abs(h[i][j]-grip[i][j]) for i in range(3) for j in range(3)),
   'finger_local_matrix_error':localerr,'wrist_bend_deg':math.degrees(desired.angle(fore)),
   'length_error_mm':1000*max(abs(a-b) for a,b in zip(lengths0,lengths))})
 # The palm/finger surface itself must move with the grip. Include vertices
 # whose complete weight comes from the hand/finger hierarchy, no arm seam.
 scene.frame_set(0);bpy.context.view_layer.update();arms=bpy.data.objects['SK_Manny_Arms_Export']
 groups={g.index:g.name for g in arms.vertex_groups};right=set(children)|{'hand_r'}
 ids=[v.index for v in arms.data.vertices if v.groups and sum(g.weight for g in v.groups if groups[g.group] in right)>.9999]
 dg=bpy.context.evaluated_depsgraph_get()
 def surface():
  ev=arms.evaluated_get(dg);mesh=ev.to_mesh();xf=rig.pose.bones['WPN_root'].matrix.inverted()@rig.matrix_world.inverted()@ev.matrix_world
  points=[xf@mesh.vertices[i].co for i in ids];ev.to_mesh_clear();return points
 initial=surface();max_surface=0.
 for f in (8,8.125,12,20,32,60,86,100,108):
  scene.frame_set(int(f),subframe=f%1);bpy.context.view_layer.update();dg=bpy.context.evaluated_depsgraph_get()
  max_surface=max(max_surface,max((a-b).length*1000 for a,b in zip(initial,surface())))
 entry={k:max(x[k] for x in rows) for k in rows[0] if k!='frame'}
 entry['hand_surface_vertices']=len(ids);entry['max_hand_surface_motion_in_grip_mm']=max_surface;entry['samples']=rows
 report[profile]=entry
 print('QBZ_O_CHECK',profile,json.dumps({k:v for k,v in entry.items() if k!='samples'}),flush=True)
(P/'source_checks.json').write_text(json.dumps(report,indent=2))
