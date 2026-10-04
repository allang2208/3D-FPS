"""Requested geometry inspection preview; no UE/game launch."""
import bpy
from pathlib import Path
from mathutils import Vector
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/HangingBellM09Meshy20261003/ArmContinuityV16')
OUT=ROOT/'Inspection/Frames';OUT.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'Authoring/M09_Claw_Continuous_V16.blend'))
scene=bpy.context.scene;scene.render.engine='BLENDER_WORKBENCH'
scene.display.shading.light='STUDIO';scene.display.shading.color_type='OBJECT'
scene.display.shading.show_cavity=True;scene.display.shading.cavity_type='BOTH'
if not scene.world:scene.world=bpy.data.worlds.new('ClawPreviewWorld')
scene.world.color=(.14,.16,.18);scene.display.shading.background_type='WORLD'
scene.view_settings.view_transform='Standard';scene.render.resolution_x=640;scene.render.resolution_y=640
scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG'
for ob in scene.objects:
    if ob.type=='MESH':
        ob.color=(.43,.43,.43,1)
        if ob.name=='M09_SmallArm_L':ob.color=(.80,.42,.20,1)
        if ob.name=='M09_SmallArm_R':ob.color=(.20,.55,.72,1)
camdata=bpy.data.cameras.new('M09ClawContinuity');cam=bpy.data.objects.new('M09ClawContinuity',camdata)
scene.collection.objects.link(cam);scene.camera=cam;camdata.type='ORTHO';camdata.ortho_scale=1.45
cam.location=(1.8,-4,1.20);target=Vector((0,-.35,1.02))
cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler()
for i in range(0,67,2):
    scene.frame_set(i+1);scene.render.filepath=str(OUT/f'claw_{i:02d}.png');bpy.ops.render.render(write_still=True)
print('M09_CLAW_CONTINUITY_PREVIEW_RENDERED',flush=True)
