from pathlib import Path
O=Path(__file__).resolve().parent
code=(O.parent/'M24ArmRebuild20261027/preview.py').read_text().split('for name,role,f,view in ')[0].replace("O/'M24_ArmRebuild_Editable.blend'", "O/'M24_GripFinish_Editable.blend'")
exec(compile(code,'preview_setup','exec'))
folder=O/'Playback';folder.mkdir(exist_ok=True);s.render.resolution_x=640;s.render.resolution_y=360
for f in range(0,56,2):
 pose('fire',f);r.matrix_world=cs@C;cam.location=(0,0,0);cam.rotation_euler=(math.pi/2,0,0);cam.data.type='PERSP'
 s.render.filepath=str(folder/f'camera_{f:03d}.png');bpy.ops.render.render(write_still=True)
 r.matrix_world=Matrix.Identity(4);target=r.pose.bones['WPN_BoltHandle'].matrix.translation
 cam.location=target+Vector((.30,-.13,.20));cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=.42
 s.render.filepath=str(folder/f'side_{f:03d}.png');bpy.ops.render.render(write_still=True)
