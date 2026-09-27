"""Diagnostic source-pose comparison, no animation or game assets are saved."""
import math,json
from pathlib import Path
import bpy
P=Path(__file__).parent
source=P.parents[1]/'RuneSword20260913/InspectRhythmContactV80/AzureRunesword_InspectRhythmContactV80.blend'
bpy.ops.wm.open_mainfile(filepath=str(source))
s=bpy.context.scene;rig=bpy.data.objects['SK_RuneSword_Rig']
arms=bpy.data.objects['V7_BareArms_AnimationSurface'];blade=bpy.data.objects['RuneSword_Blade']
for o in s.objects:o.hide_render=o not in (arms,blade)
arms.hide_set(False);blade.hide_set(False)
arms.color=(.64,.39,.27,1);blade.color=(.40,.57,.72,1)
s.render.engine='BLENDER_WORKBENCH';s.display.shading.light='STUDIO'
s.display.shading.color_type='OBJECT';s.display.shading.show_shadows=True
s.display.shading.show_cavity=True;s.display.shading.cavity_type='BOTH'
s.display.shading.background_type='WORLD';s.world.color=(.045,.052,.068)
s.render.resolution_x=768;s.render.resolution_y=432;s.render.resolution_percentage=100
s.render.image_settings.file_format='PNG'
data=bpy.data.cameras.new('DownstrokeCamera');cam=bpy.data.objects.new('DownstrokeCamera',data)
s.collection.objects.link(cam);s.camera=cam
cam.location=(0,0,0);cam.rotation_euler=(math.pi/2,0,0)
data.sensor_fit='VERTICAL';data.sensor_height=24;data.lens=24/(2*math.tan(math.radians(75/2)))
data.clip_start=.005
out=P/'Frames';out.mkdir(exist_ok=True)
rows=[]
for i,t in enumerate([.20,.24,.28,.32,.36,.40,.44,.48]):
    f=t*120;s.frame_set(int(f),subframe=f%1);bpy.context.view_layer.update()
    rows.append({'seconds':t,'hand_r':list(rig.pose.bones['hand_r'].matrix.translation),
                 'lowerarm_r':list(rig.pose.bones['lowerarm_r'].matrix.translation)})
    s.render.filepath=str(out/f'pose_{i:02}.png');bpy.ops.render.render(write_still=True)
(P/'source_render_poses.json').write_text(json.dumps(rows,indent=2))
print('DOWNSTROKE_SOURCE_STUDY_COMPLETE')
