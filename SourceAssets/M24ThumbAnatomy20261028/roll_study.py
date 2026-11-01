from pathlib import Path
exec(compile((Path(__file__).parent/'library.py').read_text(),'library','exec'))
code=(OUT.parent/'M24ArmRebuild20261027/preview.py').read_text()
exec(compile(code[code.index('def angle'):code.index('for name,role,f,view in ')],'render_setup','exec'))
folder=OUT/'Roll';folder.mkdir(exist_ok=True)
for f in (20,34):
 for roll in (-60,-40,0,40,60):
  row=thumb(clips['fire'][f],[Q(x=roll,y=-15,z=25),Q(z=10),Q(z=10)]);set_pose(row);morphs();r.matrix_world=Matrix.Identity(4)
  frame=row['hand_r'].to_3x3()@rest['hand_r'].to_3x3().inverted()@target_frame
  target=row['hand_r'].translation+frame.col[0]*.065
  for ob in s.objects:
   if ob.type=='MESH' and ob!=skin:ob.hide_render=True
  cam.location=target-frame.col[2]*.30+frame.col[1]*.04
  cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=.22
  s.render.filepath=str(folder/f'roll_{roll}_{f:03d}_hand.png');bpy.ops.render.render(write_still=True)
  for ob in s.objects:
   if ob.type=='MESH' and ob!=skin:ob.hide_render=False
  target=(row['thumb_02_r'].translation+row['index_01_r'].translation)*.5;cam.location=target+Vector((.20,-.12,.14))
  cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=.18
  s.render.filepath=str(folder/f'roll_{roll}_{f:03d}_gun.png');bpy.ops.render.render(write_still=True)
