"""Requested inspection of the installed V79 author animation, no UE launch."""
import json, math, sys
from pathlib import Path
import bpy
from mathutils import Vector
P = Path(__file__).parent
sys.path.insert(0, str(P))
from visible_bare import attach
source = P.parent/'InspectForwardSpinV54/AzureRunesword_InspectForwardSpinV79.blend'
bpy.ops.wm.open_mainfile(filepath=str(source))
s = bpy.context.scene
rig = bpy.data.objects['SK_RuneSword_Rig']
blade = bpy.data.objects['RuneSword_Blade']
arms = attach(rig)
for ob in s.objects:
    ob.hide_render = ob not in (arms, blade)
blade.hide_set(False)
blade.color = (.40,.57,.72,1)
s.render.engine='BLENDER_WORKBENCH'
s.display.shading.light='STUDIO'
s.display.shading.color_type='OBJECT'
s.display.shading.show_shadows=True
s.display.shading.show_cavity=True
s.display.shading.cavity_type='BOTH'
s.display.shading.background_type='WORLD'
s.world.color=(.045,.052,.068)
s.render.resolution_x=640
s.render.resolution_y=400
s.render.resolution_percentage=100
s.render.image_settings.file_format='PNG'
data=bpy.data.cameras.new('StudyCamera')
cam=bpy.data.objects.new('StudyCamera',data)
s.collection.objects.link(cam)
cam.location=(0,0,0)
cam.rotation_euler=(math.pi/2,0,0)
data.sensor_fit='VERTICAL'; data.sensor_height=24
data.lens=24/(2*math.tan(math.radians(75/2)))
data.clip_start=.005
s.camera=cam
out=P/'StudyV79';out.mkdir(exist_ok=True)
times=[0,.30,.40,.445,.488,.544,.616,.704,.80,.88,.94,1.04]
rows=[]
for i,t in enumerate(times):
    f=t*120;s.frame_set(int(f),subframe=f%1)
    bpy.context.view_layer.update()
    hand=rig.pose.bones['hand_r'].matrix.translation
    rows.append({'t':t,'hand':list(hand),'weapon':list(rig.pose.bones['WPN_root'].matrix.translation)})
    cam.location=(0,0,0);cam.rotation_euler=(math.pi/2,0,0);data.type='PERSP'
    s.render.filepath=str(out/f'wide_{i:02}.png');bpy.ops.render.render(write_still=True)
    # Keep the player's viewing direction, enlarge the working hand and hilt.
    cam.location=hand+Vector((0,-.70,.025))
    cam.rotation_euler=(hand-cam.location).to_track_quat('-Z','Y').to_euler()
    data.type='ORTHO';data.ortho_scale=.40
    s.render.filepath=str(out/f'grip_{i:02}.png');bpy.ops.render.render(write_still=True)
(out/'poses.json').write_text(json.dumps(rows,indent=2))
print('STUDY_V79_COMPLETE')
