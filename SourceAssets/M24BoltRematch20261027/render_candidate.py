from pathlib import Path
O=Path(__file__).resolve().parent
code=(O.parent/'M24ArmRebuild20261027/preview.py').read_text().split('for name,role,f,view in ')[0]
code=code.replace("O/'M24_ArmRebuild_Editable.blend'", "O/'M24_BoltRematch_Editable.blend'")
exec(compile(code,'preview_setup','exec'))
folder=O/'CandidateFrames';folder.mkdir(exist_ok=True)
for role,frames in [('fire',[8,12,16,19,24,29,34,39,43,48]),('reload_empty',[64,68,77,87,94,100])]:
 for f in frames:
  pose(role,f);r.matrix_world=Matrix.Identity(4)
  target=r.pose.bones['WPN_BoltHandle'].matrix.translation
  cam.location=target+Vector((.30,-.13,.20));cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=.42
  s.render.filepath=str(folder/f'{role}_{f}_side.png');bpy.ops.render.render(write_still=True)
  r.matrix_world=cs@C;cam.location=(0,0,0);cam.rotation_euler=(math.pi/2,0,0);cam.data.type='PERSP'
  s.render.filepath=str(folder/f'{role}_{f}_camera.png');bpy.ops.render.render(write_still=True)
