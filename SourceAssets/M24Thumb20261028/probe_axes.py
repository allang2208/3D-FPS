from pathlib import Path
exec(compile((Path(__file__).parent/'library.py').read_text(),'library','exec'))
P=points(rest);report={}
for n in thumb_names+['index_03_r','middle_03_r']:
 ix=dominant==names.index(n)
 local=np.array(rest[n].inverted());p=P[ix]@local[:3,:3].T+local[:3,3]
 report[n]={'skin_mean_local_mm':(p.mean(0)*1000).tolist(),'skin_min_local_mm':(p.min(0)*1000).tolist(),'skin_max_local_mm':(p.max(0)*1000).tolist(),'native_local_offset_mm':list(local_rest[n].translation*1000),'rest_rotation':list(local_rest[n].to_quaternion())}
(OUT/'native_axes.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
code=(OUT.parent/'M24ArmRebuild20261027/preview.py').read_text()
exec(compile(code[code.index('def angle'):code.index('for name,role,f,view in ')],'render_setup','exec'))
folder=OUT/'Candidates';folder.mkdir(exist_ok=True)
for f in (7,20,29,39):
 for mode in ('rest','held'):
  row={n:m.copy() for n,m in clips['fire'][f].items()}
  n='thumb_03_r';orig=row[parents[n]].inverted()@row[n]
  q=local_rest[n].to_quaternion() if mode=='rest' else (clips['fire'][0][parents[n]].inverted()@clips['fire'][0][n]).to_quaternion()
  row[n]=row[parents[n]]@Matrix.LocRotScale(orig.translation,q,orig.to_scale())
  set_pose(row);morphs();r.matrix_world=Matrix.Identity(4)
  target=row['thumb_02_r'].translation;cam.location=target+Vector((.23,-.12,.14));cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=.17
  s.render.filepath=str(folder/f'{mode}_{f:03d}.png');bpy.ops.render.render(write_still=True)
