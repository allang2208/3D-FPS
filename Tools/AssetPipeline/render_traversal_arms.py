import bpy,math,json
from pathlib import Path
from mathutils import Vector
OUT=Path('D:/FPS3D/FPSGAME/SourceAssets/GASPTraversal20260910/Native')
bpy.ops.wm.open_mainfile(filepath=str(OUT/'TraversalArms_Editable.blend'))
r=bpy.data.objects['SK_M4_Infima'];s=bpy.context.scene
for o in s.objects:o.hide_render=o.name!='SK_Manny_Arms_Export'
d=bpy.data.cameras.new('TraversalReview');cam=bpy.data.objects.new('TraversalReview',d);s.collection.objects.link(cam);s.camera=cam
s.render.engine='BLENDER_WORKBENCH';s.display.shading.light='STUDIO';s.display.shading.color_type='MATERIAL';s.display.shading.show_cavity=True
s.render.resolution_x=640;s.render.resolution_y=480;s.render.resolution_percentage=100
d.type='PERSP';d.lens=20;d.clip_start=.005
report=json.loads((OUT/'authoring.json').read_text())
for clip,info in report['clips'].items():
 a=bpy.data.actions['Traversal_'+clip];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0]
 for f in [0,round(info['contact']*60),round(info['release']*60),round(info['duration']*60)]:
  s.frame_set(f);bpy.context.view_layer.update()
  head=r.matrix_world@r.pose.bones['head'].head
  for view in ['fps','side']:
   if view=='fps':
    cam.location=head+Vector((0,-.12,.03));cam.rotation_euler=Vector((0,1,-.6)).to_track_quat('-Z','Y').to_euler()
   else:
    focus=(r.pose.bones['hand_l'].head+r.pose.bones['hand_r'].head)*.5
    cam.location=focus+Vector((1,-1,.5));cam.rotation_euler=(focus-cam.location).to_track_quat('-Z','Y').to_euler()
   s.render.filepath=str(OUT/f'{clip}_{f}_{view}.png');bpy.ops.render.render(write_still=True)
