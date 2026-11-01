import bpy,json,math
from pathlib import Path
from mathutils import Matrix,Vector
O=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(O/'M24_Hold_Editable.blend'),use_scripts=False)
s=bpy.context.scene;r=bpy.data.objects['M24_V9_Rig'];s.frame_set(0)
for ob in s.objects:
    if ob.type=='MESH':ob.color=(.61,.68,.75,1) if ob.name=='M24_V9_BareArms' else (.16,.19,.22,1)
s.render.engine='BLENDER_WORKBENCH';s.display.shading.light='STUDIO';s.display.shading.color_type='OBJECT'
s.display.shading.show_shadows=True;s.display.shading.show_cavity=True
s.display.shading.background_type='WORLD';s.world=bpy.data.worlds.new('Hold');s.world.color=(.045,.055,.07)
s.render.resolution_x=1280;s.render.resolution_y=720;s.render.resolution_percentage=100
s.render.image_settings.file_format='PNG';s.render.use_compositing=False;s.render.use_sequencer=False;s.view_settings.view_transform='Standard'
bpy.ops.object.camera_add();cam=bpy.context.object;s.camera=cam
cam.data.sensor_fit='VERTICAL';cam.data.sensor_height=24;cam.data.lens=24/(2*math.tan(math.radians(75/2)));cam.data.clip_start=.01
cam.location=(0,0,0);cam.rotation_euler=(math.pi/2,0,0)
convert=Matrix.Diagonal((100,-100,100,1));cs=Matrix(((0,.01,0,0),(.01,0,0,0),(0,0,.01,0),(0,0,0,1)))
frame=Matrix(json.loads((O/'hip-calibration.json').read_text())['hip_transform'])
r.matrix_world=cs@frame@convert;bpy.context.view_layer.update()
s.render.filepath=str(O/'Candidate/calibrated_hip.png');bpy.ops.render.render(write_still=True)
# Intermediate control group, excluding the stock which should leave the screen.
frame.translation.x-=10
r.matrix_world=cs@frame@convert;bpy.context.view_layer.update()
s.render.filepath=str(O/'Candidate/nearer_hip.png');bpy.ops.render.render(write_still=True)
r.matrix_world=Matrix.Identity(4)
cam.location=(.72,-.12,.36);cam.rotation_euler=(Vector((0,.16,.08))-cam.location).to_track_quat('-Z','Y').to_euler()
cam.data.type='ORTHO';cam.data.ortho_scale=.95
for role,f in [('fire',30),('cycle',30),('reload',30),('reload_empty',65),('inspect',45)]:
    a=bpy.data.actions['A_M24_'+role];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0]
    s.frame_set(f);bpy.context.view_layer.update()
    s.render.filepath=str(O/('Candidate/'+role+'.png'));bpy.ops.render.render(write_still=True)
