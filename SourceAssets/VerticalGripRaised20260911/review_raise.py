import bpy,json
from pathlib import Path
from mathutils import Matrix,Vector
O=Path(__file__).parent
for label,path in [('before',O.parent/'VerticalGripClass20260911/vertical/A_M4_Vertical_idle.blend'),('after',O/'vertical/A_M4_Vertical_idle.blend')]:
 bpy.ops.wm.open_mainfile(filepath=str(path));s=bpy.context.scene;r=bpy.data.objects['SK_M4_Infima'];s.frame_set(0);bpy.context.view_layer.update();G=r.pose.bones['WPN_root'].matrix@Matrix(json.loads((O/'vertical/fit_final.json').read_text())['grip_in_root']);focus=G@Vector((-.20,.07,-.12))
 for ob in s.objects:ob.hide_render=not(ob.name.startswith(('VG_','PH_')) or (ob.type=='MESH' and ob.parent==r and not ob.name.startswith('Drum')))
 d=bpy.data.cameras.new('LeftSupportReview');c=bpy.data.objects.new('LeftSupportReview',d);s.collection.objects.link(c);s.camera=c;d.type='ORTHO';d.ortho_scale=.72;d.clip_start=.001;c.location=focus+G.to_3x3()@Vector((-.05,-.8,.25));c.rotation_euler=(focus-c.location).to_track_quat('-Z','Y').to_euler()
 for p in [(-.6,-.2,.9),(.8,.6,.7)]:
  d=bpy.data.lights.new('Review','AREA');d.energy=70;d.size=1;o=bpy.data.objects.new('Review',d);s.collection.objects.link(o);o.location=p;o.rotation_euler=(focus-o.location).to_track_quat('-Z','Y').to_euler()
 s.render.engine='BLENDER_EEVEE';s.render.resolution_x=1100;s.render.resolution_y=850;s.render.resolution_percentage=100;s.render.filepath=str(O/(label+'_top.png'));bpy.ops.render.render(write_still=True)
