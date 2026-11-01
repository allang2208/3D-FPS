from pathlib import Path
exec(compile((Path(__file__).parent/'library.py').read_text(),'library','exec'))
code=(OUT.parent/'M24ArmRebuild20261027/preview.py').read_text()
exec(compile(code[code.index('def angle'):code.index('for name,role,f,view in ')],'render_setup','exec'))
folder=OUT/'Before';folder.mkdir(exist_ok=True);report={}
for f in (0,7,12,16,20,24,29,34,39,43,48,52,55):
 row=clips['fire'][f];set_pose(row);morphs();r.matrix_world=Matrix.Identity(4)
 report[str(f)]={}
 for n in thumb_names:
  q=local_rest[n].to_quaternion().inverted()@(row[parents[n]].inverted()@row[n]).to_quaternion();sw,tw=q.to_swing_twist('X')
  report[str(f)][n]={'native_relative_swing_deg':math.degrees(min(sw.angle,2*math.pi-sw.angle)),'axial_twist_deg':math.degrees(tw)}
 target=row['thumb_02_r'].translation
 for view,offset in [('side',(.23,-.12,.14)),('palm',(-.16,-.16,-.08))]:
  cam.location=target+Vector(offset);cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=.17
  s.render.filepath=str(folder/f'fire_{f:03d}_{view}.png');bpy.ops.render.render(write_still=True)
(OUT/'thumb_before.json').write_text(json.dumps(report,indent=2));print('THUMB_SOURCE_READ',flush=True)
