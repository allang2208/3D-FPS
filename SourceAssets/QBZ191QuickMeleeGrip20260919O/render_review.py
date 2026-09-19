import bpy,math
from pathlib import Path
from mathutils import Vector
P=Path(__file__).parent;out=P/'Review';out.mkdir(exist_ok=True)
for rev,source in [('N',P.parent/'RifleQuickMelee20260919/QBZ191/Base/QBZ191_QuickCombat_Base_Editable.blend'),
                   ('O',P/'Base/QBZ191_QuickCombat_Base_Editable.blend')]:
 bpy.ops.wm.open_mainfile(filepath=str(source));r=bpy.data.objects['SK_M4_Infima'];s=bpy.context.scene
 for ob in s.objects:
  if ob.type in ('MESH','ARMATURE','FONT'):
   keep=ob==r or (ob.type=='MESH' and any(m.type=='ARMATURE' and m.object==r for m in ob.modifiers))
   ob.hide_render=not keep
   if ob.name in bpy.context.view_layer.objects:ob.hide_set(not keep)
   if keep and ob.type=='MESH':ob.color=(.55,.64,.75,1) if 'Arms' in ob.name else (.16,.20,.23,1)
 camdata=bpy.data.cameras.new('GripReview');cam=bpy.data.objects.new('GripReview',camdata);s.collection.objects.link(cam);s.camera=cam
 camdata.clip_start=.001
 s.render.engine='BLENDER_WORKBENCH';s.display.shading.light='STUDIO';s.display.shading.color_type='OBJECT'
 s.display.shading.show_shadows=True;s.display.shading.show_cavity=True;s.display.shading.cavity_type='BOTH'
 s.display.shading.background_type='WORLD';s.world.color=(.075,.075,.075)
 s.render.resolution_x=640;s.render.resolution_y=440;s.render.resolution_percentage=100
 s.render.image_settings.file_format='PNG'
 for f in (0,12,20,60):
  s.frame_set(f);bpy.context.view_layer.update()
  for view in ('fp','grip'):
   if view=='fp':
    cam.location=(-.07,0,.07);cam.rotation_euler=(math.pi/2,0,0);camdata.type='PERSP';camdata.lens=13.2
   else:
    root=r.matrix_world@r.pose.bones['WPN_root'].matrix
    # Camera follows the weapon: before/after reveal contact in the same frame.
    h=r.pose.bones['hand_r'].matrix if f==0 else None
    if f==0:hand_local=r.pose.bones['WPN_root'].matrix.inverted()@h
    center=root@hand_local.translation
    cam.location=center+root.to_3x3()@Vector((-.35,.15,.12))
    cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler();camdata.type='ORTHO';camdata.ortho_scale=.33
   s.render.filepath=str(out/f'{rev}_{view}_{f:03}.png');bpy.ops.render.render(write_still=True)
print('QBZ_GRIP_REVIEW_RENDERED',flush=True)
