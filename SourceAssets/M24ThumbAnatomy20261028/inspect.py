from pathlib import Path
exec(compile((Path(__file__).parent/'library.py').read_text(),'library','exec'))
code=(OUT.parent/'M24ArmRebuild20261027/preview.py').read_text()
exec(compile(code[code.index('def angle'):code.index('for name,role,f,view in ')],'render_setup','exec'))
folder=OUT/'Inspect';folder.mkdir(exist_ok=True);info={}
for f in (0,7,16,20,25,30,34,39,43,48):
 row=clips['fire'][f];info[str(f)]={}
 for n in thumb_names:
  q=local_rest[n].to_quaternion().inverted()@(row[parents[n]].inverted()@row[n]).to_quaternion()
  info[str(f)][n]={'basis_xyz_deg':[math.degrees(x) for x in q.to_euler('XYZ')],'basis_quat':list(q)}
 set_pose(row);morphs();r.matrix_world=Matrix.Identity(4)
 target=(row['thumb_02_r'].translation+row['index_01_r'].translation)*.5
 for view,off in [('back',(.20,-.12,.14)),('palm',(.20,.14,.03))]:
  cam.location=target+Vector(off);cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=.18
  s.render.filepath=str(folder/f'before_{f:03d}_{view}.png');bpy.ops.render.render(write_still=True)
(OUT/'thumb_joints_before.json').write_text(json.dumps(info,indent=2));print('M24_THUMB_JOINTS',json.dumps(info),flush=True)
# Native anatomical candidates, all three thumb joints, same wrist/arm/gun.
for name,bases in [('native',[Q(),Q(),Q()]),('relaxed',[Q(y=-10,z=-5),Q(z=5),Q(z=5)]),('opposed',[Q(x=12,y=-15,z=10),Q(z=12),Q(z=10)]),('raised',[Q(x=0,y=10,z=-10),Q(z=5),Q(z=5)])]:
 for f in (20,30,39):
  row=thumb(clips['fire'][f],bases);set_pose(row);morphs();r.matrix_world=Matrix.Identity(4)
  target=(row['thumb_02_r'].translation+row['index_01_r'].translation)*.5
  cam.location=target+Vector((.20,-.12,.14));cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=.18
  s.render.filepath=str(folder/f'{name}_{f:03d}.png');bpy.ops.render.render(write_still=True)
