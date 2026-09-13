import bpy,json,math
from pathlib import Path
from mathutils import Matrix,Vector
O=Path(__file__).parent;S=O.parent;out={}
bpy.ops.wm.open_mainfile(filepath=str(S/'QBZ19120260912/QBZ191_Editable.blend'));r=bpy.data.objects['SK_M4_Infima'];s=bpy.context.scene
out['constraints']={b.name:[c.name for c in b.constraints] for b in r.pose.bones if len(b.constraints)}
out['hierarchy']={b.name:b.parent.name if b.parent else None for b in r.pose.bones}
out['jumps']={}
for name in ['QBZ191_reload','QBZ191_reload_empty','QBZ191_equip_charge']:
 a=bpy.data.actions[name];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0];last=None;jumps=[]
 for k in range(int(a.frame_range[1]*2)+1):
  f=k/2;s.frame_set(int(f),subframe=f%1);bpy.context.view_layer.update();p={b.name:b.matrix.copy() for b in r.pose.bones}
  if last:
   for n in ['WPN_root','upperarm_l','lowerarm_l','hand_l','hand_r']:
    q0=last[n].to_quaternion();q1=p[n].to_quaternion();ang=math.degrees(q0.rotation_difference(q1).angle);ang=min(ang,360-ang)
    if ang>12:jumps.append([f,n,round(ang,2),round((last[n].translation-p[n].translation).length,4)])
  last=p
 out['jumps'][name]=jumps
out['attachments']={}
for key in ['vertical','canted','prism','angled','panoramic_red_dot','holographic','prism_scope_2x','lpvo_1_6x']:
 bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.fbx(filepath=str(O/(key+'.fbx')))
 pts=[o.matrix_world@v.co for o in bpy.context.scene.objects if o.type=='MESH' for v in o.data.vertices]
 out['attachments'][key]={'min':[min(v[i] for v in pts) for i in range(3)],'max':[max(v[i] for v in pts) for i in range(3)]}
 # Keep Blender world geometry in metres. Its FBX axes are measured, not guessed.
 mesh=next(o for o in bpy.context.scene.objects if o.type=='MESH');out['attachments'][key]['matrix']=[list(row) for row in mesh.matrix_world]
bpy.ops.wm.open_mainfile(filepath=str(S/'QBZ19120260912/SourceInspect.blend'));o=bpy.data.objects['QBZ'];xf=Matrix.Translation((-.005,-.11,.065));pts=[xf@o.matrix_world@v.co for v in o.data.vertices]
# Actual top and bottom rail cross-sections along the handguard and receiver.
out['rail_sections']={}
for y in [-.34,-.32,-.30,-.28,-.26,-.24,-.22,-.20,-.18,-.16,-.14,-.12,-.10,-.08,-.06,-.04]:
 near=[v for v in pts if abs(v.y-y)<.005 and abs(v.x)<.016]
 out['rail_sections'][str(y)]={'min_z':min(v.z for v in near),'max_z':max(v.z for v in near)} if near else None
(O/'authoring_measurements.json').write_text(json.dumps(out,indent=2));print('QBZ_AUTHORING_MEASUREMENTS_READY',flush=True)
