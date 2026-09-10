"""Render an actual skeletal animation preview, preserving source playback timing."""
import bpy,runpy
from pathlib import Path
from mathutils import Vector
ROOT=Path(r'D:\FPS3D\FPSGAME')
OUT=ROOT/'SourceAssets/AKMReplacement'
# Reuse the reviewed lighting/camera setup. This also refreshes the pose stills.
ns=runpy.run_path(str(ROOT/'Tools/AssetPipeline/render_akm_replacement.py'))
rig=ns['rig'];scene=ns['scene'];camera=ns['camera'];camera_data=ns['camera_data']
for o in bpy.data.objects:
    if o.type=='MESH' and o.parent==rig:o.hide_render=False
scene.render.resolution_x=960;scene.render.resolution_y=600;scene.render.resolution_percentage=100
camera_data.type='PERSP';camera_data.lens=43
center=Vector((.02,.32,-.08));camera.location=center+Vector((1.00,-1.20,.65))
camera.rotation_euler=(center-camera.location).to_track_quat('-Z','Y').to_euler()
frames_dir=OUT/'motion_frames';frames_dir.mkdir(exist_ok=True)
for i,f in enumerate(range(1,105,2)):
    ns['set_pose']('reload_empty',f)
    scene.render.filepath=str(frames_dir/f'reload_empty_{i:03d}.png')
    bpy.ops.render.render(write_still=True)
print('AKM_REPLACEMENT_MOTION_FRAMES_OK '+str(frames_dir))
