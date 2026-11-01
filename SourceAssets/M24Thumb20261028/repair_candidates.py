from pathlib import Path
exec(compile((Path(__file__).parent/'library.py').read_text(),'library','exec'))
digits3=[f'{d}_03_r' for d in ('thumb','index','middle','ring','pinky')]
report={}
for f in (0,7,16,20,24,29,34,39,43):
 row=clips['fire'][f];report[str(f)]={}
 for n in digits3:
  loc=row[parents[n]].inverted()@row[n];q=local_rest[n].to_quaternion().inverted()@loc.to_quaternion()
  report[str(f)][n]={'angle_deg':math.degrees(min(q.angle,2*math.pi-q.angle)),'basis_quat':list(q)}
(OUT/'fingers_before.json').write_text(json.dumps(report,indent=2))
code=(OUT.parent/'M24ArmRebuild20261027/preview.py').read_text()
exec(compile(code[code.index('def angle'):code.index('for name,role,f,view in ')],'render_setup','exec'))
folder=OUT/'Candidates';folder.mkdir(exist_ok=True)
for f in (7,16,20,24,29,34,39,43):
 row={n:m.copy() for n,m in clips['fire'][f].items()}
 for n in digits3:
  if n=='index_03_r' and f in (7,43):continue # Index was deliberately held during release.
  old=row[n].copy();base=row[parents[n]]@local_rest[n]
  current=base.to_quaternion()@Vector((-1,0,0));desired=old.to_quaternion()@Vector((1,0,0))
  newq=current.rotation_difference(desired)@base.to_quaternion()
  loc=row[parents[n]].inverted()@old
  row[n]=row[parents[n]]@Matrix.LocRotScale(loc.translation,row[parents[n]].to_quaternion().inverted()@newq,loc.to_scale())
 set_pose(row);morphs();r.matrix_world=Matrix.Identity(4)
 target=row['thumb_02_r'].translation
 for view,offset in [('side',(.23,-.12,.14)),('palm',(-.12,-.14,-.14))]:
  cam.location=target+Vector(offset);cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=.20
  s.render.filepath=str(folder/f'axisfix_{f:03d}_{view}.png');bpy.ops.render.render(write_still=True)
