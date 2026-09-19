import bpy,json
from pathlib import Path
from mathutils import Vector
O=Path(__file__).parent;bpy.ops.wm.open_mainfile(filepath=str(O/'AKM_Attachments_Editable.blend'))
r=bpy.data.objects['SK_M4_Infima'];s=bpy.context.scene;a=bpy.data.actions['AKM_Native_idle'];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0];s.frame_set(0)
parts=json.loads((O/'parts.json').read_text());s.render.engine='BLENDER_WORKBENCH';s.display.shading.color_type='MATERIAL';s.display.shading.show_cavity=True;s.render.resolution_x=1200;s.render.resolution_y=800;s.render.resolution_percentage=100
d=bpy.data.cameras.new('Fit');cam=bpy.data.objects.new('Fit',d);s.collection.objects.link(cam);s.camera=cam;d.type='ORTHO';d.ortho_scale=1.0
for key in ['optic','drum','prism','angled','suppressor']:
 bpy.data.objects['AKM_FactoryMagazine_Preview'].hide_render=key=='drum'
 for k,n in parts.items():bpy.data.objects[n].hide_render=k!=key
 bpy.data.objects['SK_Manny_Arms_Export'].hide_render=True
 target=r.matrix_world@r.pose.bones['WPN_root'].matrix@Vector((0,-.20,.025));cam.location=target+Vector((.65,-.6,.38));cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();s.render.filepath=str(O/f'fit_{key}.png');bpy.ops.render.render(write_still=True)
print('PART_REVIEW_PASS')
