from pathlib import Path
exec(compile((Path(__file__).parent/'library.py').read_text(),'library','exec'))
final={role:[{n:Matrix(m) for n,m in row.items()} for row in rows] for role,rows in json.loads((OUT/'final_poses.json').read_text()).items()}
code=(OUT.parent/'M24ArmRebuild20261027/preview.py').read_text()
exec(compile(code[code.index('def angle'):code.index('for name,role,f,view in ')],'render_setup','exec'))
folder=OUT/'Compare';folder.mkdir(exist_ok=True);s.render.resolution_x=640;s.render.resolution_y=420
for f in range(0,56,2):
 for stage,rows in [('before',clips['fire']),('after',final['fire'])]:
  row=rows[f];set_pose(row);morphs();r.matrix_world=Matrix.Identity(4)
  for ob in s.objects:
   if ob.type=='MESH' and ob!=skin:ob.hide_render=True
  frame=row['hand_r'].to_3x3()@rest['hand_r'].to_3x3().inverted()@target_frame
  target=row['hand_r'].translation+frame.col[0]*.065
  cam.location=target-frame.col[2]*.30+frame.col[0]*.10+frame.col[1]*.04
  cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=.20
  s.render.filepath=str(folder/f'{stage}_{f:03d}.png');bpy.ops.render.render(write_still=True)
print('M24_THUMB_ANATOMY_COMPARE_RENDERED',flush=True)
