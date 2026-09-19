import bpy,json
from pathlib import Path
from mathutils import Vector,Matrix
O=Path(__file__).parent
bpy.ops.wm.open_mainfile(filepath=str(O/'A_M4_Prism_idle.blend'));r=bpy.data.objects['SK_M4_Infima'];s=bpy.context.scene
for clip in json.loads((O/'animation_build.json').read_text()):
 if clip=='idle':continue
 name='A_M4_Prism_'+clip
 with bpy.data.libraries.load(str(O/(name+'.blend')),link=False) as (src,dst):dst.actions=[name]
 dst.actions[0].use_fake_user=True
a=bpy.data.actions['A_M4_Prism_idle'];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0];s.frame_set(0)
for ob in s.objects:ob.hide_render=not(ob.name.startswith('PH_') or (ob.type=='MESH' and ob.parent==r))
d=bpy.data.cameras.new('GraspReview');cam=bpy.data.objects.new('GraspReview',d);s.collection.objects.link(cam);s.camera=cam;d.type='ORTHO';d.ortho_scale=.44;d.clip_start=.001
G=r.pose.bones['WPN_root'].matrix@Matrix(json.loads((O/'fit_final.json').read_text())['grip_in_root']);focus=G@Vector((0,0,0));cam.location=focus+Vector((.4,-.12,.10));cam.rotation_euler=(focus-cam.location).to_track_quat('-Z','Y').to_euler()
for position in [(-.6,-.2,.9),(.8,.6,.7)]:
 d=bpy.data.lights.new('Review','AREA');d.energy=70;d.size=1;ob=bpy.data.objects.new('Review',d);s.collection.objects.link(ob);ob.location=position;ob.rotation_euler=(focus-ob.location).to_track_quat('-Z','Y').to_euler()
s.render.engine='BLENDER_EEVEE';s.render.resolution_x=1100;s.render.resolution_y=850;s.render.resolution_percentage=100
bpy.ops.wm.save_as_mainfile(filepath=str(O/'M4_Prism_Family_Editable.blend'))
s.render.filepath=str(O/'final_grasp.png');bpy.ops.render.render(write_still=True)
cam.location=focus+Vector((-.4,-.12,.12));cam.rotation_euler=(focus-cam.location).to_track_quat('-Z','Y').to_euler();s.render.filepath=str(O/'final_grasp_back.png');bpy.ops.render.render(write_still=True)
print('FOREGRIP_EDITABLE_READY')
