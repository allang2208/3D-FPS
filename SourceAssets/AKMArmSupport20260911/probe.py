import bpy,json,math
from pathlib import Path
from mathutils import Vector
O=Path(__file__).parent;report={}
for variant in ['prism','angled']:
 bpy.ops.wm.open_mainfile(filepath=str(O.parent/'AKMAttachments20260911'/variant/f'A_AKM_{variant}_idle.blend'))
 r=bpy.data.objects['SK_M4_Infima'];s=bpy.context.scene;s.frame_set(0);p=r.pose.bones;b=r.data.bones
 A,E,H=[p[n].matrix.translation for n in ['upperarm_l','lowerarm_l','hand_l']]
 direction=p['hand_l'].matrix.to_3x3()@b['hand_l'].matrix_local.to_3x3().inverted()@(b['hand_l'].head_local-b['lowerarm_l'].head_local).normalized()
 l1=(E-A).length;l2=(H-E).length;ideal=H-direction*l2
 delta=ideal+(A-ideal).normalized()*l1-A
 report[variant]={'bend':math.degrees((H-E).angle(direction)),'shoulder_delta':list(delta),'A':list(A),'E':list(E),'H':list(H),'lengths':[l1,l2]}
 s.render.engine='BLENDER_WORKBENCH';s.display.shading.color_type='MATERIAL';s.display.shading.show_cavity=True;s.render.resolution_x=1000;s.render.resolution_y=700;s.render.resolution_percentage=100
 d=bpy.data.cameras.new('Wrist');c=bpy.data.objects.new('Wrist',d);s.collection.objects.link(c);s.camera=c;d.type='ORTHO';d.ortho_scale=.63
 target=r.matrix_world@(H.lerp(E,.4));c.location=target+Vector((-.6,.25,.35));c.rotation_euler=(target-c.location).to_track_quat('-Z','Y').to_euler();s.render.filepath=str(O/f'{variant}_before.png');bpy.ops.render.render(write_still=True)
(O/'probe.json').write_text(json.dumps(report,indent=2));print('ARM_PROBE_PASS',report)
