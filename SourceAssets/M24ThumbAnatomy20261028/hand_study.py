from pathlib import Path
exec(compile((Path(__file__).parent/'library.py').read_text(),'library','exec'))
code=(OUT.parent/'M24ArmRebuild20261027/preview.py').read_text()
exec(compile(code[code.index('def angle'):code.index('for name,role,f,view in ')],'render_setup','exec'))
folder=OUT/'HandStudy';folder.mkdir(exist_ok=True)
for ob in s.objects:
 if ob.type=='MESH' and ob!=skin:ob.hide_render=True
thumb_vids=selected[np.where(digit_masks['thumb'])[0]];key_report={}
for key in skin.data.shape_keys.key_blocks:
 if not key.name.startswith(('JC_Grip','JC_Pose')):continue
 maximum=max((key.data[int(i)].co-skin.data.shape_keys.key_blocks[0].data[int(i)].co).length for i in thumb_vids)
 if maximum>.00005:key_report[key.name]=maximum*1000
(OUT/'thumb_corrective_shapes.json').write_text(json.dumps(key_report,indent=2))
for f in (20,34,36):
 src=clips['fire'][f]
 proximal=src['thumb_02_r'].to_quaternion();root_world=proximal@(local_rest['thumb_02_r'].to_quaternion()@Q(z=2)).inverted()
 root_basis=local_rest['thumb_01_r'].to_quaternion().inverted()@src['hand_r'].to_quaternion().inverted()@root_world
 options={'before':src,'transfer':thumb(src,[root_basis,Q(z=2),Q(z=6)]),'cup':thumb(src,[Q(y=-25,z=40),Q(z=5),Q(z=6)]),'gentle':thumb(src,[Q(y=6,z=-8),Q(z=6),Q(z=6)])}
 for name,row in options.items():
  set_pose(row);morphs();r.matrix_world=Matrix.Identity(4)
  frame=row['hand_r'].to_3x3()@rest['hand_r'].to_3x3().inverted()@target_frame
  target=row['hand_r'].translation+frame.col[0]*.065
  for view,sign in [('palm',1),('back',-1)]:
   cam.location=target+frame.col[2]*(sign*.30)+frame.col[1]*.04
   cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=.22
   s.render.filepath=str(folder/f'{name}_{f:03d}_{view}.png');bpy.ops.render.render(write_still=True)
print('M24_HAND_STUDY',key_report,flush=True)
